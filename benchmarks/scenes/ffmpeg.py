#!/usr/bin/env python3
"""Pass explicit x264 settings to the FFmpeg process used by ManimGL."""

import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
assert "libx264" in args, args
assert "rawvideo" in args, args
command = [
    "ffmpeg",
    *args[:-1],
    "-preset",
    "ultrafast",
    "-crf",
    "23",
    args[-1],
]
Path(os.environ["MANIMGX_BENCH_FFMPEG_LOG"]).write_text(
    json.dumps(command, indent=2) + "\n", encoding="utf-8"
)
os.execvp(command[0], command)
