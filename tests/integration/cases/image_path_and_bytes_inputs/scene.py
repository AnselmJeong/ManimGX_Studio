# Source: custom ImageMobject constructor coverage
import pathlib
from typing import TypedDict

import manimgx as m

_CASE_DIR = pathlib.Path(__file__).resolve().parent
_IMAGE_PATH = _CASE_DIR / "checker.ppm"


class _StrokeKwargs(TypedDict, total=False):
    stroke_width: int
    stroke_color: str


def _bytes_or_path() -> pathlib.Path | bytes:
    if m.__name__ == "manimgx":
        return _IMAGE_PATH.read_bytes()
    return _IMAGE_PATH


def _stroke_kwargs(color: str) -> _StrokeKwargs:
    # CE's ImageMobject rejects stroke_width/stroke_color; manimgx accepts them.
    if m.__name__ == "manimgx":
        return {"stroke_width": 6, "stroke_color": color}
    return {}


class ImagePathAndBytesInputs(m.Scene):
    def construct(self):
        path_image = m.ImageMobject(_IMAGE_PATH, **_stroke_kwargs(m.WHITE))
        # `_bytes_or_path` only returns `bytes` when running under manimgx
        # (which accepts bytes); under manim CE the branch returns a path.
        # ty can't narrow through `m.__name__ == "manimgx"`.
        bytes_image = m.ImageMobject(
            _bytes_or_path(),
            **_stroke_kwargs(m.YELLOW),
        )

        path_image.height = 3.4
        bytes_image.height = 3.4

        path_label = m.Text("path", font_size=36).next_to(path_image, m.DOWN)
        bytes_label = m.Text("bytes", font_size=36).next_to(bytes_image, m.DOWN)

        group = m.Group()
        group.add(path_image, bytes_image)
        group.arrange(m.RIGHT, buff=0.8)
        path_label.next_to(path_image, m.DOWN)
        bytes_label.next_to(bytes_image, m.DOWN)

        self.add(group, path_label, bytes_label)
        self.play(
            path_image.animate.rotate(0.18).shift(0.35 * m.UP),
            bytes_image.animate.rotate(-0.18).shift(0.35 * m.DOWN),
            run_time=1.2,
        )
        self.wait(0.4)
