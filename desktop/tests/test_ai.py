"""AI boundary and workflow regressions; real provider calls are never used."""

import copy
import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from ai_worker import (
    CODE_SCHEMA,
    INSTRUCTIONS,
    create_film,
    validate_plan,
    validate_source,
)
from codex_client import Codex, allowance, environment


@pytest.fixture
def provider(tmp_path, monkeypatch):
    cli = tmp_path / "codex"
    fixture = Path(__file__).with_name("fake_codex.py").read_text()
    cli.write_text(f"#!{sys.executable}\n" + fixture)
    cli.chmod(0o755)
    monkeypatch.setenv("MANIMGX_STUDIO_CODEX", str(cli))
    home = tmp_path / "codex-home/codex"
    home.mkdir(parents=True)
    return tmp_path / "codex-home", home


def scenario(provider, **values):
    (provider[1] / "scenario.json").write_text(json.dumps(values))


def calls(provider):
    return [
        json.loads(line)["method"]
        for line in (provider[1] / "trace.jsonl").read_text().splitlines()
    ]


def test_environment_strips_credentials_and_injection(monkeypatch):
    for key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "CODEX_AUTH_TOKEN",
        "NODE_OPTIONS",
    ):
        monkeypatch.setenv(key, "sentinel")
        assert key not in environment()


@pytest.mark.parametrize(
    ("allowed", "used"),
    [(False, 0), (None, 0), (True, 100), (True, -1), (True, float("nan"))],
)
def test_quota_denial_never_starts_a_thread(provider, allowed, used):
    scenario(provider, allowed=allowed, used=used)
    client = Codex(provider[0], threading.Event())
    try:
        with pytest.raises(RuntimeError):
            client.generate("hello", CODE_SCHEMA, INSTRUCTIONS, "")
        assert "thread/start" not in calls(provider)
    finally:
        client.close()


def test_secondary_and_model_exhaustion_override_positive_allowance():
    for exhausted in (
        {"secondary": {"usedPercent": 100}},
        {"normalModelSlug": "chosen", "primary": {"usedPercent": 100}},
    ):
        response = {
            "ordinaryUsageAllowed": True,
            "rateLimitsByLimitId": {
                "codex": {"primary": {"usedPercent": 0}},
                "chosen": exhausted,
            },
        }
        if "normalModelSlug" not in exhausted:
            response["rateLimitsByLimitId"]["codex"].update(exhausted)
        with pytest.raises(RuntimeError):
            allowance(response, "chosen")


def test_api_key_auth_is_rejected(provider):
    scenario(provider, auth="apiKey")
    client = Codex(provider[0], threading.Event())
    try:
        with pytest.raises(RuntimeError, match="로그인"):
            client.generate("hello", CODE_SCHEMA, INSTRUCTIONS, "")
        assert "thread/start" not in calls(provider)
    finally:
        client.close()


def test_early_deltas_and_duplicate_final_deliver_once(provider):
    client = Codex(provider[0], threading.Event())
    try:
        result = client.generate("hello", CODE_SCHEMA, INSTRUCTIONS, "")
        assert "class Lesson" in result["source"]
        assert calls(provider).count("turn/start") == 1
    finally:
        client.close()


@pytest.mark.parametrize("values", [{"turn_status": "failed"}, {"tool": True}])
def test_failed_completion_and_tools_do_not_succeed(provider, values):
    scenario(provider, **values)
    client = Codex(provider[0], threading.Event())
    try:
        with pytest.raises(RuntimeError):
            client.generate("hello", CODE_SCHEMA, INSTRUCTIONS, "")
    finally:
        client.close()


def test_malformed_transport_and_cancel_settle(provider):
    scenario(provider, initialize="malformed")
    with pytest.raises(ValueError, match=r"."):
        Codex(provider[0], threading.Event())
    scenario(provider, initialize="hang")
    cancelled = threading.Event()
    timer = threading.Timer(0.2, cancelled.set)
    timer.start()
    with pytest.raises(InterruptedError):
        Codex(provider[0], cancelled)
    timer.cancel()


@pytest.mark.parametrize(
    "source",
    [
        "import os",
        "import pathlib",
        "import numpy as np\nnp.load('secret')",
        "x.__class__",
        "getattr(x, 'write')",
        "exec('x')",
    ],
)
def test_generated_code_rejects_system_access(source):
    with pytest.raises(ValueError, match=r"."):
        validate_source(source + "\nclass Lesson: pass\n")


def test_plan_duration_is_bounded():
    with pytest.raises(ValueError, match=r"."):
        validate_plan(
            {
                "title": "x",
                "summary": "x",
                "scenes": [{"title": "a", "description": "b", "seconds": float("nan")}],
            }
        )


def test_workflow_repairs_then_preserves_revision_and_history(provider):
    client = Codex(provider[0], threading.Event())
    project = {
        "version": 1,
        "id": "same",
        "title": "original",
        "scene": "Lesson",
        "source": "old source",
        "lesson_id": "custom",
        "last_render": None,
        "plan": [],
        "summary": "",
        "conversation": [],
    }
    original = copy.deepcopy(project)
    request = {"project": project, "prompt": "노란색으로 바꿔 줘", "model": ""}
    directory = provider[0] / "renders/123-456"
    directory.mkdir(parents=True)
    events = []
    try:
        with (
            patch(
                "ai_worker.render", side_effect=[ValueError("bad geometry"), directory]
            ) as renderer,
            patch(
                "ai_worker.emit",
                side_effect=lambda kind, **values: events.append((kind, values)),
            ),
        ):
            create_film(client, request, provider[0], threading.Event())
        assert project == original
        assert renderer.call_count == 2
        result = next(value["project"] for kind, value in events if kind == "result")
        assert "YELLOW" in result["source"]
        assert result["revisions"][0]["source"] == "old source"
        assert result["conversation"][0]["text"] == request["prompt"]
        assert result["last_render"] == "123-456"
        assert calls(provider).count("turn/start") == 3
    finally:
        client.close()


def test_render_failure_preserves_project_and_limits_repairs(provider):
    client = Codex(provider[0], threading.Event())
    project = {
        "id": "same",
        "title": "original",
        "source": "old source",
        "conversation": [],
    }
    original = copy.deepcopy(project)
    try:
        with (
            patch(
                "ai_worker.render", side_effect=ValueError("bad geometry")
            ) as renderer,
            pytest.raises(RuntimeError, match="두 번"),
        ):
            create_film(
                client,
                {"project": project, "prompt": "make film"},
                provider[0],
                threading.Event(),
            )
        assert renderer.call_count == 3
        assert project == original
    finally:
        client.close()


def test_sandbox_denies_outside_files_and_network(tmp_path):
    import subprocess

    from ai_worker import sandbox_command

    run = tmp_path / "run"
    run.mkdir()
    secret = tmp_path / "outside.txt"
    secret.write_text("private")
    argv, env = sandbox_command(run)
    code = f"""import socket
from pathlib import Path
for operation in [lambda: Path({str(secret)!r}).read_text(), lambda: Path({str(tmp_path / "outside-write")!r}).write_text('no'), lambda: socket.create_connection(('127.0.0.1', 9), timeout=1)]:
    try:
        operation()
    except PermissionError:
        continue
    raise RuntimeError('sandbox did not deny access')
print('sandbox boundaries verified')
"""
    result = subprocess.run(
        argv[:3] + [sys.executable, "-c", code],
        cwd=run,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert "verified" in result.stdout


def test_cancel_interrupts_a_quiet_turn_and_reaps_process(provider):
    import time

    scenario(provider, quiet_turn=True)
    cancelled = threading.Event()
    client = Codex(provider[0], cancelled)
    timer = threading.Timer(0.3, cancelled.set)
    started = time.monotonic()
    timer.start()
    try:
        with pytest.raises(InterruptedError):
            client.generate("hello", CODE_SCHEMA, INSTRUCTIONS, "")
    finally:
        client.close()
        timer.cancel()
    assert client.child.poll() is not None
    assert time.monotonic() - started < 5


def test_unavailable_model_never_falls_back(provider):
    client = Codex(provider[0], threading.Event())
    try:
        with pytest.raises(RuntimeError, match="모델"):
            client.generate("hello", CODE_SCHEMA, INSTRUCTIONS, "missing-model")
        assert "thread/start" not in calls(provider)
    finally:
        client.close()
