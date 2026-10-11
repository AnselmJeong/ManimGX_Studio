"""Render five scenes sequentially through the engines' native MP4 exporters."""

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path
from threading import Timer

from benchmarks.scenes.suite_data import DURATIONS, FPS, HEIGHT, WIDTH

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "scenes"
TOOLS = ("manimgx", "manimgl", "manim_ce", "blender_workbench", "blender_eevee")
REPEATS = {tool: 3 if tool in ("manimgx", "manimgl") else 1 for tool in TOOLS}


@dataclass
class Run:
    scene: str
    tool: str
    repeat: int
    command: list[str]
    status: str = "pending"
    wall_seconds: float = 0
    cpu_seconds: float = 0
    log: str = ""
    error: str = ""
    video: dict[str, str | int | float] = field(default_factory=dict)


def executable(value: str) -> str:
    path = shutil.which(value)
    if path is None:
        raise FileNotFoundError(f"Executable not found: {value}")
    return str(Path(path).absolute())


def command(tool: str, scene: str, folder: Path, args: argparse.Namespace) -> list[str]:
    source = SOURCES / (
        f"{scene}_{tool}.py"
        if scene in ("orbit", "matrix", "pendulums")
        else "suite_manim.py"
    )
    cls = (
        "Orbit"
        if scene == "orbit"
        else "TeacherScene"
        if scene in ("matrix", "pendulums")
        else "Benchmark"
    )
    if tool == "manimgx":
        return [
            args.gx,
            "render",
            str(source),
            cls,
            "-o",
            str(folder / "out.mp4"),
            "--preset",
            "ultrafast",
            "--crf",
            "23",
            "--resolution",
            f"{WIDTH}x{HEIGHT}",
            "--fps",
            str(FPS),
        ]
    if tool == "manim_ce":
        return [
            args.ce_python,
            str(SOURCES / "ce_cli.py"),
            "render",
            "-qh",
            "--disable_caching",
            "--media_dir",
            str(folder),
            str(source),
            cls,
        ]
    if tool == "manimgl":
        config = folder / "config.yml"
        config.write_text(
            f'directories:\n  cache: {json.dumps(str(folder / "cache"))}\ncamera:\n  background_color: "#000000"\n  fps: {FPS}\ntex:\n  template: "basic"\nfile_writer:\n  ffmpeg_bin: {json.dumps(str(SOURCES / "ffmpeg.py"))}\n',
            encoding="utf-8",
        )
        return [
            args.manimgl,
            str(source),
            cls,
            "-w",
            "--hd",
            "--video_dir",
            str(folder),
            "--config_file",
            str(config),
        ]
    name = (
        "orbit_blender.py"
        if scene == "orbit"
        else "two_d_blender.py"
        if scene in ("matrix", "pendulums")
        else "linked_rings_blender.py"
        if scene == "linked_rings"
        else "suite_blender.py"
    )
    engine = tool.removeprefix("blender_")
    cmd = [
        args.blender,
        "-b",
        "--factory-startup",
        "--python-exit-code",
        "1",
        "-P",
        str(SOURCES / name),
        "--",
        "--engine",
        engine.upper() if scene == "orbit" else engine,
        "--out",
        str(folder / "out.mp4"),
    ]
    if scene == "linked_rings":
        cmd += ["--animate"]
    elif scene != "orbit":
        cmd += ["--scene", scene]
    return cmd


def encoder_evidence(path: Path, tool: str) -> str:
    match = re.search(rb"x264 - core [^\x00]{1,3000}", path.read_bytes())
    if match is None and tool == "manimgx":
        return "Explicit ultrafast / CRF 23 CLI arguments"
    evidence = match.group().decode("ascii", errors="replace") if match else ""
    required = (
        ("crf=23.0", "subme=1", "me=dia", "bframes=0")
        if tool.startswith("blender_")
        else ("crf=23.0", "cabac=0", "subme=0", "bframes=0")
    )
    if not all(
        re.search(rf"\b{re.escape(value)}(?:\s|$)", evidence) for value in required
    ):
        raise ValueError(f"Unexpected encoder options: {evidence}")
    return evidence


def validate(path: Path, tool: str, duration: float) -> dict[str, str | int | float]:
    """Decode the complete video and check its timeline and encoder settings."""
    import av

    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=r_frame_rate",
                "-of",
                "json",
                str(path),
            ],
            text=True,
        )
    )
    if Fraction(probe["streams"][0]["r_frame_rate"]) != FPS:
        raise ValueError("Unexpected frame rate")
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        if stream.codec_context.name != "h264" or stream.time_base is None:
            raise ValueError("Expected H.264 with presentation timestamps")
        stream.thread_type = "AUTO"
        stream.codec_context.thread_count = 2
        previous, end, decoded = -1, 0, 0
        for frame in container.decode(stream):
            if (frame.width, frame.height, frame.format.name) != (
                WIDTH,
                HEIGHT,
                "yuv420p",
            ):
                raise ValueError("Unexpected resolution or pixel format")
            if (
                frame.pts is None
                or frame.pts <= previous
                or (decoded == 0 and frame.pts != 0)
            ):
                raise ValueError("Invalid presentation timestamps")
            previous, end = frame.pts, frame.pts + frame.duration
            decoded += 1
        timeline = end * stream.time_base * FPS
        if not decoded or end <= previous or abs(timeline - round(duration * FPS)) > 1:
            raise ValueError(f"Unexpected video timeline: {timeline} frames")
    return {
        "path": str(path),
        "decoded_frames": decoded,
        "timeline_frames": float(timeline),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "encoder_evidence": encoder_evidence(path, tool),
    }


def run_one(tool: str, scene: str, repeat: int, args: argparse.Namespace) -> Run:
    folder = args.out / scene / tool / str(repeat)
    folder.mkdir(parents=True, exist_ok=False)
    cmd = command(tool, scene, folder, args)
    result = Run(scene, tool, repeat, cmd, log=str(folder / "render.log"))
    if args.dry_run:
        result.status = "planned"
        return result
    if not hasattr(os, "wait4"):
        raise RuntimeError("the benchmark runner measures CPU time on macOS and Linux")
    env = os.environ | {
        "BENCH_ENGINE": tool,
        "BENCH_SCENE": scene,
        "BENCH_DURATION": str(DURATIONS[scene]),
        "PYTHONPATH": str(SOURCES),
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(folder),
        "MANIMGX_BENCH_PRESET": "ultrafast",
        "MANIMGX_BENCH_CRF": "23",
        "MANIMGX_BENCH_FFMPEG_LOG": str(folder / "ffmpeg-command.json"),
    }
    timed_out = False
    with Path(result.log).open("wb") as log:
        start = time.perf_counter()
        process = subprocess.Popen(
            cmd,
            cwd=folder,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        def expire() -> None:
            nonlocal timed_out
            timed_out = True
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)

        watchdog = Timer(args.timeout, expire)
        watchdog.start()
        try:
            _, status, usage = os.wait4(process.pid, 0)
        finally:
            result.wall_seconds = time.perf_counter() - start
            watchdog.cancel()
            watchdog.join()
        process.returncode = os.waitstatus_to_exitcode(status)
    result.cpu_seconds = usage.ru_utime + usage.ru_stime
    if timed_out or process.returncode:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        result.status = "timeout" if timed_out else "failed"
        result.error = Path(result.log).read_text(encoding="utf-8", errors="replace")[
            -4000:
        ]
        return result
    try:
        videos = [
            p for p in folder.rglob("*.mp4") if "partial_movie_files" not in p.parts
        ]
        if len(videos) != 1:
            raise ValueError(f"Expected one MP4, found {len(videos)}")
        result.video = validate(videos[0], tool, DURATIONS[scene])
        result.status = "complete"
    except Exception as error:
        result.status, result.error = "invalid", str(error)
    return result


def summarize(
    runs: list[Run], scenes: list[str], repeats: dict[str, int]
) -> dict[str, object]:
    per_scene = {}
    for scene in scenes:
        per_scene[scene] = {}
        for tool in repeats:
            samples = [
                r.wall_seconds
                for r in runs
                if r.scene == scene and r.tool == tool and r.status == "complete"
            ]
            if len(samples) == repeats[tool]:
                per_scene[scene][tool] = {
                    "mean_seconds": statistics.mean(samples),
                    "samples_seconds": samples,
                }
    totals = {
        tool: sum(per_scene[scene][tool]["mean_seconds"] for scene in scenes)
        for tool in repeats
        if all(tool in per_scene[scene] for scene in scenes)
    }
    return {
        "per_scene": per_scene,
        "totals": totals,
        "complete": len(totals) == len(repeats),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tools", nargs="+", choices=TOOLS, default=list(TOOLS))
    parser.add_argument(
        "--scenes", nargs="+", choices=DURATIONS, default=list(DURATIONS)
    )
    parser.add_argument(
        "--rounds",
        type=int,
        help="Runs per scene and engine; default: three for GX/GL, one for CE/Blender",
    )
    parser.add_argument("--gx", default=str(Path(sys.executable).parent / "manimgx"))
    parser.add_argument("--ce-python", default=sys.executable)
    parser.add_argument("--manimgl", default="manimgl")
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write commands without starting renderers",
    )
    args = parser.parse_args()
    if (args.rounds is not None and args.rounds < 1) or args.timeout <= 0:
        parser.error("Rounds and timeout must be positive")
    args.scenes, args.tools = (
        list(dict.fromkeys(args.scenes)),
        list(dict.fromkeys(args.tools)),
    )
    if not args.dry_run:
        for tool, option in (
            ("manimgx", "gx"),
            ("manim_ce", "ce_python"),
            ("manimgl", "manimgl"),
            ("blender", "blender"),
        ):
            if any(name.startswith(tool) for name in args.tools):
                setattr(args, option, executable(getattr(args, option)))
        executable("ffmpeg")
        executable("ffprobe")
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    repeats = {tool: args.rounds or REPEATS[tool] for tool in args.tools}
    manifest = {
        "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "machine": {
            "os": platform.platform(),
            "cpu": platform.processor(),
            "cpus": os.cpu_count(),
        },
        "settings": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "crf": 23,
            "manim_preset": "ultrafast",
            "blender_preset": "REALTIME",
            "scenes": {s: DURATIONS[s] for s in args.scenes},
            "repeats": repeats,
        },
        "source_sha256": {
            str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.rglob("*.py"))
        },
    }
    runs: list[Run] = []
    for scene in args.scenes:
        for repeat in range(1, max(repeats.values()) + 1):
            for tool in args.tools:
                if repeat > repeats[tool]:
                    continue
                print(f"{scene}: {tool}, run {repeat}", flush=True)
                row = run_one(tool, scene, repeat, args)
                runs.append(row)
                result = (
                    manifest
                    | summarize(runs, args.scenes, repeats)
                    | {"runs": [asdict(r) for r in runs]}
                )
                temp = args.out / "results.tmp"
                temp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                temp.replace(args.out / "results.json")
                print(
                    f"  {row.status}"
                    + (f" {row.wall_seconds:.3f}s" if not args.dry_run else ""),
                    flush=True,
                )
                if row.status not in ("complete", "planned"):
                    raise SystemExit(row.error or row.status)


if __name__ == "__main__":
    main()
