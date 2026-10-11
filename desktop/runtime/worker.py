"""Render with the real ManimGX CLI, then prepare bounded native preview frames."""

import json
import math
import sys
from pathlib import Path


def write_json(path: Path, value: object) -> None:
    """Replace a status or manifest only after the complete JSON is written."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def preview(video: Path, directory: Path) -> dict[str, object]:
    """Decode at most 240 sampled frames, bounded to a 768-pixel-wide image."""
    import av

    frames: list[str] = []
    times: list[float] = []
    with av.open(str(video)) as container:
        stream = container.streams.video[0]
        duration = (
            float(stream.duration * stream.time_base)
            if stream.duration is not None and stream.time_base is not None
            else float(container.duration or 0) / av.time_base
        )
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("영상의 길이를 읽을 수 없습니다.")
        interval = max(1 / 12, duration / 239)
        next_time = 0.0
        for frame in container.decode(stream):
            moment = float(frame.time or 0)
            if moment + 0.0001 < next_time or len(frames) >= 240:
                continue
            filename = f"frame-{len(frames):04d}.jpg"
            image = frame.to_image()
            image.thumbnail((768, 432))
            image.save(directory / filename, quality=86)
            frames.append(filename)
            times.append(moment)
            next_time += interval
        if not frames:
            raise ValueError("영상에서 미리보기 프레임을 읽을 수 없습니다.")
        return {
            "duration": duration,
            "width": stream.width,
            "height": stream.height,
            "fps": float(stream.average_rate or 30),
            "frames": frames,
            "times": times,
        }


def main() -> None:
    """Arguments are isolated paths and validated render settings from the desktop host."""
    if len(sys.argv) != 5:
        raise ValueError("worker.py RUN_DIRECTORY RESOLUTION FPS SCENE_NAME")
    directory = Path(sys.argv[1]).resolve()
    resolution, fps, scene_name = sys.argv[2:]
    video = directory / "film.mp4"
    write_json(directory / "status.json", {"phase": "ManimGX로 영상 렌더링 중"})
    from manimgx.cli import main as cli

    sys.argv = [
        "manimgx",
        "render",
        str(directory / "scene.py"),
        scene_name,
        "-r",
        resolution,
        "--fps",
        fps,
        "-o",
        str(video),
    ]
    try:
        cli()
    except SystemExit as error:
        if error.code not in (None, 0):
            raise
    if not video.is_file() or video.stat().st_size == 0:
        raise ValueError("ManimGX가 MP4 파일을 만들지 못했습니다.")
    write_json(directory / "status.json", {"phase": "영상 미리보기 준비 중"})
    manifest = preview(video, directory)
    write_json(directory / "preview.json", manifest)
    write_json(directory / "status.json", {"phase": "완료"})


if __name__ == "__main__":
    main()
