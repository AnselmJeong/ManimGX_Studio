"""Deterministic Codex subprocess fixture; no network, credentials or quota."""

import json
import os
import sys
from pathlib import Path

if "--version" in sys.argv:
    print("codex-cli fixture-0.160.0")
    sys.exit(0)
home = Path(os.environ["CODEX_HOME"])
scenario = (
    json.loads((home / "scenario.json").read_text())
    if (home / "scenario.json").exists()
    else {}
)


def write(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False), flush=True)


for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    with (home / "trace.jsonl").open("a") as trace:
        trace.write(json.dumps(request) + "\n")
    if "id" not in request:
        continue
    result = {}
    if method == "initialize":
        assert not any(
            key in os.environ
            for key in (
                "OPENAI_API_KEY",
                "OPENAI_BASE_URL",
                "NODE_OPTIONS",
                "CODEX_AUTH_TOKEN",
            )
        )
        if scenario.get("initialize") == "hang":
            import time

            time.sleep(20)
        if scenario.get("initialize") == "malformed":
            print("bad frame", flush=True)
            continue
    if method == "account/read":
        result = {"account": {"type": scenario.get("auth", "chatgpt")}}
    if method == "model/list":
        result = {
            "data": [
                {
                    "id": "catalog-id",
                    "model": "fixture-model",
                    "displayName": "Fixture model",
                    "isDefault": True,
                    "hidden": False,
                    "defaultReasoningEffort": "low",
                    "inputModalities": ["text", "image"],
                }
            ],
            "nextCursor": None,
        }
    if method == "account/rateLimits/read":
        result = {
            "ordinaryUsageAllowed": scenario.get("allowed", True),
            "rateLimitsByLimitId": {
                "codex": {
                    "primary": {
                        "usedPercent": scenario.get("used", 10),
                        "windowDurationMins": 300,
                    },
                    "secondary": None,
                }
            },
        }
    if method == "thread/start":
        assert request["params"]["ephemeral"]
        assert request["params"]["sandbox"] == "read-only"
        result = {"thread": {"id": "thread-fixture"}}
    if method == "turn/start":
        params = request["params"]
        if "scenes" in params["outputSchema"]["properties"]:
            content = {
                "title": "빛의 굴절",
                "summary": "굴절률이 다른 두 매질을 지나는 빛",
                "scenes": [
                    {
                        "title": "굴절 관찰",
                        "description": "빛의 진행 방향 변화를 표시합니다.",
                        "seconds": 2,
                    }
                ],
            }
        else:
            prompt = params["input"][0]["text"]
            color = "YELLOW" if "노란색" in prompt else "BLUE"
            source = f"import manimgx as m\nclass Lesson(m.Scene):\n    def construct(self):\n        ray = m.Arrow(m.LEFT * 2, m.RIGHT * 2, color=m.{color})\n        self.play(m.Create(ray), run_time=1)\n        self.wait(1)\n"
            content = {"source": source, "message": "빛의 이동을 표시했습니다."}
        if scenario.get("tool"):
            write(
                {
                    "id": 99,
                    "method": "item/commandExecution/requestApproval",
                    "params": {},
                }
            )
        text = json.dumps(content, ensure_ascii=False)
        write(
            {
                "method": "item/agentMessage/delta",
                "params": {
                    "threadId": "thread-fixture",
                    "turnId": "turn-fixture",
                    "itemId": "answer",
                    "delta": text,
                },
            }
        )
        result = {"turn": {"id": "turn-fixture"}}
        write({"id": request["id"], "result": result})
        if scenario.get("quiet_turn"):
            import time

            time.sleep(20)
        write(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "thread-fixture",
                    "turnId": "turn-fixture",
                    "item": {"id": "answer", "type": "agentMessage", "text": text},
                },
            }
        )
        write(
            {
                "method": "turn/completed",
                "params": {
                    "threadId": "thread-fixture",
                    "turn": {
                        "id": "turn-fixture",
                        "status": scenario.get("turn_status", "completed"),
                        "error": None,
                    },
                },
            }
        )
        continue
    write({"id": request["id"], "result": result})
