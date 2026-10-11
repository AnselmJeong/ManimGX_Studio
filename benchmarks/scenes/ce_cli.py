"""Set x264 options on each CE partial stream before any frames are submitted."""

import os

from manim.__main__ import main
from manim.scene.scene_file_writer import SceneFileWriter

original = SceneFileWriter.open_partial_movie_stream


def open_stream(self, file_path=None):
    original(self, file_path)
    stream = self._current_encode_job.stream
    stream.options = dict(stream.options) | {
        "preset": os.environ.get("MANIMGX_BENCH_PRESET", "ultrafast"),
        "crf": "23",
    }


SceneFileWriter.open_partial_movie_stream = open_stream
main()
