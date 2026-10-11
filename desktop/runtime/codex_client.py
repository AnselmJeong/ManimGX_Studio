"""App-private, tool-free Codex App Server transport (CLI 0.160.0)."""

import contextlib
import json
import math
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

MAX_FRAME = 3_000_000


def emit(kind: str, **values: object) -> None:
    print(json.dumps({"kind": kind, **values}, ensure_ascii=False), flush=True)


def environment() -> dict[str, str]:
    keys = (
        "HOME",
        "USER",
        "LOGNAME",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "PATH",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
    )
    return {key: os.environ[key] for key in keys if key in os.environ}


def discover() -> Path:
    candidates = [
        os.environ.get("MANIMGX_STUDIO_CODEX", ""),
        str(Path.home() / ".local/bin/codex"),
        "/opt/homebrew/bin/codex",
        "/usr/local/bin/codex",
        "/Applications/Codex.app/Contents/Resources/codex",
        shutil.which("codex") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return Path(candidate)
    raise RuntimeError(
        "Codex CLI를 찾지 못했습니다. Codex를 설치한 뒤 AI 연결을 새로고침하세요."
    )


def allowance(response: dict, model: str) -> str:
    """Fail closed; credits and elapsed reset dates never grant included usage."""
    if response.get("ordinaryUsageAllowed") is not True:
        raise RuntimeError(
            "구독 사용 가능 여부를 확인하지 못했거나 사용 한도에 도달했습니다. AI 연결을 새로고침하세요."
        )
    buckets = response.get("rateLimitsByLimitId") or {
        "codex": response.get("rateLimits")
    }
    relevant = [
        value
        for key, value in buckets.items()
        if isinstance(value, dict)
        and (
            value.get("normalModelSlug") == model
            or (not value.get("normalModelSlug") and key == "codex")
        )
    ]
    windows = []
    for bucket in relevant:
        if bucket.get("spendControlReached") is True:
            raise RuntimeError("계정의 사용 한도에 도달했습니다.")
        for key in ("primary", "secondary"):
            window = bucket.get(key)
            if window is None:
                continue
            used = window.get("usedPercent")
            if (
                not isinstance(used, (int, float))
                or isinstance(used, bool)
                or not math.isfinite(used)
                or used < 0
            ):
                raise RuntimeError(
                    "사용량 정보가 유효하지 않습니다. AI 연결을 새로고침하세요."
                )
            if used >= 100:
                raise RuntimeError(
                    "Codex 구독 사용 한도에 도달했습니다. 한도가 갱신된 뒤 다시 시도하세요."
                )
            minutes = window.get("windowDurationMins")
            reset = window.get("resetsAt")
            label = f"{minutes}분 한도" if minutes else "구독 한도"
            suffix = (
                time.strftime(" · %m/%d %H:%M 갱신", time.localtime(reset))
                if isinstance(reset, (int, float)) and 0 < reset < 100_000_000_000
                else ""
            )
            windows.append(f"{label} {100 - used:.0f}% 남음{suffix}")
    return " / ".join(windows) or "계정에서 구독 사용 가능 확인됨"


class Codex:
    """One process per serialized UI job; caller owns cancellation and lifetime."""

    def __init__(self, data: Path, cancelled: threading.Event):
        self.cancelled = cancelled
        self.child = None
        self.sequence = 0
        self.inbox = queue.Queue(maxsize=1024)
        self.pending = []
        self.active = None
        self.login_id = None
        self.home = data / "codex"
        self.scratch = self.home / "scratch"
        for path in (self.home, self.scratch):
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o700)
        cli = discover()
        self.cli = str(cli)
        env = environment()
        env["CODEX_HOME"] = str(self.home)
        self.version = (
            subprocess.check_output(
                [str(cli), "--version"], env=env, timeout=10, stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
        settings = {
            "forced_login_method": '"chatgpt"',
            "model_provider": '"openai"',
            "cli_auth_credentials_store": '"file"',
            "approval_policy": '"never"',
            "sandbox_mode": '"read-only"',
            "web_search": '"disabled"',
            "project_doc_max_bytes": "0",
            "mcp_servers": "{}",
            "analytics.enabled": "false",
        }
        for feature in (
            "shell_tool",
            "unified_exec",
            "multi_agent",
            "apps",
            "plugins",
            "hooks",
            "code_mode",
            "code_mode_host",
            "apply_patch_freeform",
        ):
            settings[f"features.{feature}"] = "false"
        argv = [str(cli), "app-server"]
        for key, value in settings.items():
            argv.extend(["-c", f"{key}={value}"])
        self.child = subprocess.Popen(
            argv,
            cwd=self.scratch,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.reader = threading.Thread(target=self._reader, daemon=True)
        self.reader.start()
        try:
            self.rpc(
                "initialize",
                {
                    "clientInfo": {
                        "name": "manimgx_studio",
                        "title": "ManimGX Studio",
                        "version": "0.2.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            )
            self.send({"method": "initialized", "params": {}})
        except BaseException:
            self.close()
            raise

    def _reader(self) -> None:
        try:
            while True:
                line = self.child.stdout.readline(MAX_FRAME + 1)
                if not line:
                    raise RuntimeError("Codex 연결이 종료되었습니다.")
                if len(line) > MAX_FRAME:
                    raise RuntimeError("Codex 응답이 허용 크기를 초과했습니다.")
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise RuntimeError("Codex 응답 형식이 올바르지 않습니다.")
                self.inbox.put(value, timeout=2)
        except BaseException as error:
            with contextlib.suppress(queue.Full):
                self.inbox.put(error, timeout=2)

    def send(self, value: dict) -> None:
        self.child.stdin.write((json.dumps(value) + "\n").encode())
        self.child.stdin.flush()

    def receive(self, deadline: float) -> dict:
        while time.monotonic() < deadline:
            if self.cancelled.is_set():
                raise InterruptedError("작업을 중단했습니다.")
            try:
                value = self.inbox.get(timeout=0.1)
            except queue.Empty:
                continue
            if isinstance(value, BaseException):
                raise value
            if "id" in value and "method" in value:
                self.send(
                    {
                        "id": value["id"],
                        "error": {
                            "code": -32601,
                            "message": "Studio does not permit agent tools or approval requests",
                        },
                    }
                )
                raise RuntimeError("허용되지 않은 AI 도구 요청을 차단했습니다.")
            return value
        raise TimeoutError("Codex 응답 시간이 초과되었습니다. 다시 시도하세요.")

    def rpc(self, method: str, params: dict, timeout: float = 30) -> dict:
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while True:
            value = self.receive(deadline)
            if value.get("id") == request_id:
                if "error" in value:
                    raise RuntimeError(
                        f"Codex {method}: {value['error'].get('message', '요청 실패')}"
                    )
                return value.get("result", {})
            self.pending.append(value)
            if len(self.pending) > 1024:
                raise RuntimeError("Codex 알림이 허용 크기를 초과했습니다.")

    def models(self) -> list[dict]:
        models, cursors, cursor = [], set(), None
        while True:
            result = self.rpc(
                "model/list", {"cursor": cursor, "limit": 100, "includeHidden": False}
            )
            models.extend(item for item in result["data"] if not item.get("hidden"))
            cursor = result.get("nextCursor")
            if not cursor:
                return models
            if cursor in cursors or len(models) > 500:
                raise RuntimeError("모델 목록을 읽지 못했습니다.")
            cursors.add(cursor)

    def connection(
        self, selected: str = "", required: bool = False
    ) -> tuple[dict, dict | None]:
        account = self.rpc("account/read", {"refreshToken": True}).get("account")
        status = {
            "connected": False,
            "models": [],
            "usage": "로그인이 필요합니다",
            "cli": self.cli,
            "version": self.version,
        }
        if not account or account.get("type") != "chatgpt":
            emit("connection", **status)
            if required:
                raise RuntimeError("AI 연결에서 ChatGPT로 로그인하세요.")
            return status, None
        models = self.models()
        model = (
            next((item for item in models if item["model"] == selected), None)
            if selected
            else next((item for item in models if item.get("isDefault")), None)
        )
        status.update(
            connected=True,
            models=[
                {"model": item["model"], "name": item["displayName"]} for item in models
            ],
        )
        failure = None
        try:
            if model is None:
                raise RuntimeError(
                    "선택한 모델을 사용할 수 없습니다. AI 연결에서 모델을 다시 선택하세요."
                )
            status["usage"] = allowance(
                self.rpc("account/rateLimits/read", {}), model["model"]
            )
        except (RuntimeError, TimeoutError) as error:
            failure = error
            status["usage"] = str(error)
        emit("connection", **status)
        if required and failure:
            raise failure
        return status, model

    def login(self) -> None:
        result = self.rpc("account/login/start", {"type": "chatgpt"})
        parsed = urlparse(result.get("authUrl", ""))
        if parsed.scheme != "https" or parsed.hostname not in {
            "auth.openai.com",
            "auth0.openai.com",
        }:
            raise RuntimeError("Codex 로그인 주소를 확인하지 못했습니다.")
        self.login_id = result["loginId"]
        emit("login", url=result["authUrl"])
        deadline = time.monotonic() + 600
        while True:
            event = self.pending.pop(0) if self.pending else self.receive(deadline)
            if (
                event.get("method") == "account/login/completed"
                and event["params"].get("loginId") == self.login_id
            ):
                self.login_id = None
                if not event["params"].get("success"):
                    raise RuntimeError(
                        "ChatGPT 로그인이 완료되지 않았습니다. 다시 연결하세요."
                    )
                return

    def generate(
        self,
        prompt: str,
        schema: dict,
        instructions: str,
        selected: str,
        image: str | None = None,
    ) -> dict:
        _, model = self.connection(selected, required=True)
        thread = self.rpc(
            "thread/start",
            {
                "model": model["model"],
                "cwd": str(self.scratch),
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "ephemeral": True,
                "baseInstructions": instructions,
            },
        )["thread"]["id"]
        self.pending.clear()
        inputs = [{"type": "text", "text": prompt, "text_elements": []}]
        if image and "image" in model.get("inputModalities", []):
            inputs.append({"type": "image", "url": image})
        try:
            turn = self.rpc(
                "turn/start",
                {
                    "threadId": thread,
                    "input": inputs,
                    "outputSchema": schema,
                    "effort": model["defaultReasoningEffort"],
                    "serviceTierForTurn": "default",
                },
            )["turn"]["id"]
            self.active = (thread, turn)
            deadline = time.monotonic() + 600
            items, size = {}, 0
            while True:
                event = self.pending.pop(0) if self.pending else self.receive(deadline)
                params = event.get("params", {})
                if (
                    params.get("threadId") != thread
                    or params.get("turnId", params.get("turn", {}).get("id")) != turn
                ):
                    continue
                method = event.get("method")
                if method == "item/agentMessage/delta":
                    key = params["itemId"]
                    delta = params.get("delta", "")
                    items[key] = items.get(key, "") + delta
                    size += len(delta)
                    if size > 1_000_000:
                        raise RuntimeError(
                            "생성된 장면이 너무 큽니다. 요청 범위를 줄여주세요."
                        )
                elif (
                    method == "item/completed"
                    and params["item"]["type"] == "agentMessage"
                ):
                    items[params["item"]["id"]] = params["item"]["text"]
                elif method == "turn/completed":
                    completed = params["turn"]
                    if completed["status"] != "completed":
                        raise RuntimeError(
                            (completed.get("error") or {}).get("message")
                            or "AI 생성이 완료되지 않았습니다."
                        )
                    if not items:
                        raise RuntimeError("AI가 장면을 반환하지 않았습니다.")
                    return json.loads(list(items.values())[-1])
        finally:
            self.active = None if not self.cancelled.is_set() else self.active
            if not self.cancelled.is_set():
                self.rpc("thread/unsubscribe", {"threadId": thread})

    def close(self) -> None:
        if not self.child:
            return
        try:
            if self.active:
                self.send(
                    {
                        "id": 900001,
                        "method": "turn/interrupt",
                        "params": {
                            "threadId": self.active[0],
                            "turnId": self.active[1],
                        },
                    }
                )
            if self.login_id:
                self.send(
                    {
                        "id": 900002,
                        "method": "account/login/cancel",
                        "params": {"loginId": self.login_id},
                    }
                )
            self.child.stdin.close()
            self.child.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            self.child.kill()
            self.child.wait()
        finally:
            self.reader.join(timeout=3)
            self.child.stdout.close()
