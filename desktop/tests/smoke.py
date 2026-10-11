"""Exercise every shipped lesson through the desktop's real rendering worker."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import av


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "qa-output"
    output.mkdir(exist_ok=True)
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    for lesson in sorted((root / "lessons").glob("*.py")):
        directory = output / lesson.stem
        directory.mkdir(exist_ok=True)
        shutil.copyfile(lesson, directory / "scene.py")
        with (directory / "render.log").open("w") as log:
            subprocess.run(
                [
                    sys.executable,
                    str(root / "runtime/worker.py"),
                    str(directory),
                    "960x540",
                    "24",
                    "Lesson",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=300,
            )
        manifest = json.loads((directory / "preview.json").read_text())
        assert 2 < manifest["duration"] < 60
        assert 2 < len(manifest["frames"]) <= 240
        assert manifest["width"] == 960
        assert manifest["height"] == 540
        assert all((directory / frame).is_file() for frame in manifest["frames"])
        with av.open(str(directory / "film.mp4")) as video:
            assert sum(1 for _ in video.decode(video=0)) > 48
        shutil.copyfile(
            directory / manifest["frames"][-1], assets / f"{lesson.stem}.jpg"
        )
        print(
            f"PASS {lesson.stem}: {manifest['duration']:.2f}s, {len(manifest['frames'])} preview frames",
            flush=True,
        )


if __name__ == "__main__":
    main()
