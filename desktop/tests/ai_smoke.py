"""Exercise packaged AI workers with a fake provider and real sandboxed MP4s."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_worker(python: Path, worker: Path, request: dict, env: dict[str, str]) -> dict:
    with subprocess.Popen(
        [str(python), "-u", str(worker)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    ) as child:
        child.stdin.write(json.dumps(request) + "\n")
        child.stdin.flush()
        project = None
        for line in child.stdout:
            event = json.loads(line)
            if event["kind"] == "error":
                raise RuntimeError(event["message"])
            if event["kind"] == "result":
                project = event["project"]
            if event["kind"] == "done":
                break
        child.stdin.close()
        child.wait(timeout=10)
        assert child.returncode == 0, child.stderr.read()
        assert project is not None
        return project


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    resources = root / "dist/ManimGX Studio.app/Contents/Resources"
    python = resources / "python/bin/python3"
    data = root / "qa-output/ai-packaged"
    data.mkdir(parents=True, exist_ok=True)
    fake = data / "fixture-codex"
    fake.write_text(
        f"#!{sys.executable}\n" + (root / "tests/fake_codex.py").read_text()
    )
    fake.chmod(0o755)
    env = {**os.environ, "MANIMGX_STUDIO_CODEX": str(fake)}
    project = {
        "version": 1,
        "id": "qa-ai",
        "title": "새 영상",
        "scene": "Lesson",
        "source": "",
        "lesson_id": "custom",
        "last_render": None,
    }
    for prompt in ("빛의 굴절을 설명해 줘", "빛을 노란색으로 바꿔 줘"):
        project = run_worker(
            python,
            resources / "ai_worker.py",
            {
                "action": "create",
                "data": str(data),
                "project": project,
                "prompt": prompt,
                "resolution": "640x360",
            },
            env,
        )
        run = data / "renders" / project["last_render"]
        manifest = json.loads((run / "preview.json").read_text())
        assert manifest["duration"] >= 1.9
        assert manifest["width"] == 640
        assert (run / "film.mp4").stat().st_size > 1000
        print(f"PASS {prompt}: {run / 'film.mp4'}", flush=True)
    assert "YELLOW" in project["source"]
    assert "BLUE" in project["revisions"][0]["source"]
    assert len(project["conversation"]) == 4
    (data / "result.mgx").write_text(json.dumps(project, ensure_ascii=False, indent=2))
    print(
        "PASS packaged creation, conversational revision, MP4 decode and previous-version preservation"
    )


if __name__ == "__main__":
    main()
