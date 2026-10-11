"""The configuration's frame: the video's proportions, with a short side of 8 units.

- Unless its height is set, the frame's short side is 8 units at every size of video, wide
  (16:9: about 14.2 × 8) or tall (9:16: 8 × about 14.2), and the frame has the video's
  proportions. A scene laid out in the central 8 × 8 square fits both, at the same size.
- A height that is set is the frame's height, whatever the video's proportions; the CLI's
  reset before a scene file forgets it, as it forgets every field.
- Nothing reads the configuration when ManimGX is imported: a scene's file sets the video's
  size after its import, so a default read then would be a wide video's in a tall one.
"""

import ast
import dataclasses
from pathlib import Path
from typing import assert_type

import pytest
from hypothesis import given
from hypothesis import strategies as st

import manimgx as m
from manimgx.config import Config

pixels = st.integers(16, 4096)


def test_simulation_rate_has_the_same_typed_dictionary_access_as_other_fields() -> None:
    config = Config()
    config["simulation_rate"] = 120
    assert assert_type(config["simulation_rate"], int) == config.simulation_rate == 120


@given(width=pixels, height=pixels)
def test_the_frames_short_side_is_8_units_in_the_videos_proportions(
    width: int, height: int
) -> None:
    config = Config(pixel_width=width, pixel_height=height)
    assert min(config.frame_width, config.frame_height) == pytest.approx(8)
    assert config.frame_width / config.frame_height == pytest.approx(width / height)


def test_a_tall_video_is_a_wide_one_turned() -> None:
    wide = Config(pixel_width=1920, pixel_height=1080)
    tall = Config(pixel_width=1080, pixel_height=1920)
    assert (wide.frame_width, wide.frame_height) == pytest.approx((128 / 9, 8))
    assert (tall.frame_width, tall.frame_height) == pytest.approx((8, 128 / 9))


@given(width=pixels, height=pixels, set_to=st.floats(0.5, 100))
def test_a_height_set_is_the_frames_height(
    width: int, height: int, set_to: float
) -> None:
    config = Config(pixel_width=width, pixel_height=height)
    config["frame_height"] = set_to
    assert config.frame_height == set_to
    assert config.frame_width == pytest.approx(set_to * width / height)


@pytest.mark.config(pixel_width=1080, pixel_height=1920)
def test_the_defaults_forget_a_height_set() -> None:
    m.config.frame_height = 8
    for field in dataclasses.fields(Config):
        setattr(m.config, field.name, getattr(Config(), field.name))
    m.config.pixel_width, m.config.pixel_height = 1080, 1920
    assert m.config.frame_width == pytest.approx(8)


class _AtImport(ast.NodeVisitor):
    """The lines of a module that read `config` when the module is imported."""

    def __init__(self) -> None:
        self.lines: list[int] = []

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "config" and isinstance(node.ctx, ast.Load):
            self.lines.append(node.lineno)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # its decorators and defaults run now; its body, when it is called
        for expr in [*node.decorator_list, *node.args.defaults, *node.args.kw_defaults]:
            if expr is not None:
                self.visit(expr)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for expr in [*node.args.defaults, *node.args.kw_defaults]:
            if expr is not None:
                self.visit(expr)


def test_nothing_reads_the_configuration_when_manimgx_is_imported() -> None:
    package = Path(m.__file__).parent
    reads = []
    for path in sorted(package.rglob("*.py")):
        found = _AtImport()
        found.visit(ast.parse(path.read_text(encoding="utf-8")))
        reads += [f"{path.relative_to(package)}:{line}" for line in found.lines]
    assert not reads, f"read before a scene's file can set the video: {reads}"
