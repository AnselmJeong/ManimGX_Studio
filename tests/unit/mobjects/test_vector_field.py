"""A field's color queries follow its color; stream line colors run from start to end.

A flow has one field-time phase: speed changes time once, steps compose across cycles,
restarting replaces its own updater, and ending restores whole lines in their own paint.
"""

import numpy as np
import pytest
from tests.scenes import scene

import manimgx as m
from manimgx.typing import Point3D


def flowing() -> m.StreamLines:
    return m.StreamLines(
        lambda p: m.RIGHT,
        color=m.RED,
        x_range=[0, 0, 1],
        y_range=[0, 0, 1],
        noise_factor=0,
        virtual_time=1,
        dt=0.1,
        opacity=0.4,
    )


def assert_phase(lines: m.StreamLines, phase: float) -> None:
    for line in lines.stream_lines:
        np.testing.assert_allclose(
            line.paint.trim, [1.3 * phase - 0.3, 1.3 * phase], atol=1e-14
        )


@pytest.mark.parametrize("speed", [0.5, 1, 2])
@pytest.mark.parametrize("elapsed", [0.125, 0.75, 2.75])
def test_flow_speed_only_converts_elapsed_time_once(
    speed: float, elapsed: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("random.random", lambda: 0.0)
    lines = flowing().start_animation(warm_up=False, flow_speed=speed)
    lines.update(elapsed)
    assert_phase(lines, (elapsed * speed) % 1)


@pytest.mark.parametrize("warm_up", [False, True])
def test_flow_initial_phase_and_long_steps_compose(
    warm_up: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("random.random", lambda: 0.5)
    whole, split = [flowing().start_animation(warm_up=warm_up) for _ in range(2)]
    assert_phase(whole, 0 if warm_up else 0.5)
    whole.update(2.75)
    for _ in range(11):
        split.update(0.25)
    assert_phase(whole, 0.25)
    np.testing.assert_array_equal(
        whole.stream_lines[0].paint.trim, split.stream_lines[0].paint.trim
    )


def test_restarting_a_flow_replaces_only_its_own_updater(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("random.random", lambda: 0.0)
    lines = flowing()
    calls: list[float] = []
    lines.add_updater(lambda mob, dt: calls.append(dt))
    lines.start_animation(warm_up=False)
    lines.start_animation(warm_up=False, flow_speed=2)
    assert len(lines.updaters) == 2
    lines.update(0.125)
    assert calls == [0.125]
    assert_phase(lines, 0.25)


@pytest.mark.parametrize("speed", [0, -1, float("nan"), float("inf")])
def test_invalid_speed_does_not_replace_an_active_flow(
    speed: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("random.random", lambda: 0.0)
    lines = flowing().start_animation(warm_up=False)
    active = lines.flow_animation
    with pytest.raises(ValueError, match="positive and finite"):
        lines.start_animation(flow_speed=speed)
    assert lines.flow_animation is active
    lines.update(0.25)
    assert_phase(lines, 0.25)


@pytest.mark.parametrize("duration", [0, float("inf"), float("nan")])
def test_a_flow_requires_a_finite_positive_cycle(duration: float) -> None:
    lines = flowing()
    lines.virtual_time = duration
    with pytest.raises(ValueError, match="positive and finite"):
        lines.start_animation()
    assert lines.flow_animation is None
    assert not lines.updaters


def test_ending_continues_the_current_phase_without_changing_its_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("random.random", lambda: 0.25)
    lines = flowing().start_animation(warm_up=False, flow_speed=2)
    lines.update(0.0625)
    ending = lines.end_animation()
    succession = ending.animations[0]
    assert isinstance(succession, m.Succession)
    finish = succession.animations[0]
    assert finish.run_time == (1 - 0.375) / 2
    finish.begin()
    finish.interpolate(0.5)
    assert_phase(lines, (0.375 + 1) / 2)
    finish.finish()


@pytest.mark.parametrize("warm_up", [False, True])
@pytest.mark.parametrize("speed", [0.5, 2])
@pytest.mark.parametrize("restart", [False, True])
def test_ending_a_flow_restores_whole_lines_and_their_original_paint(
    warm_up: bool, speed: float, restart: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("random.random", lambda: 0.5)
    lines = flowing()
    original = lines.stream_lines[0].copy()

    def construct(s: m.Scene) -> None:
        s.add(lines)
        lines.start_animation(warm_up=warm_up, flow_speed=speed)
        if restart:
            lines.start_animation(warm_up=warm_up, flow_speed=speed)
        s.wait(0.125)
        s.play(lines.end_animation())

    scene(construct).render()
    assert lines.flow_animation is None
    assert not lines.updaters
    for line in lines.stream_lines:
        assert line in lines.submobjects
        assert not line.updating_suspended
        np.testing.assert_array_equal(line.paint.trim, [0, 1])
        np.testing.assert_array_equal(line.paint.stroke, original.paint.stroke)


def field(kind: str, color: m.ManimColor | None = None) -> m.VectorField:
    def function(point: Point3D) -> Point3D:
        return np.array([0.2, 0.3, 0.0])

    if kind == "plain":
        return m.VectorField(function, color=color, colors=[m.RED, m.BLUE])
    if kind == "arrows":
        return m.ArrowVectorField(
            function,
            color=color,
            colors=[m.RED, m.BLUE],
            x_range=[0, 0, 1],
            y_range=[0, 0, 1],
        )
    return m.StreamLines(
        function,
        color=color,
        colors=[m.RED, m.BLUE],
        x_range=[0, 0, 1],
        y_range=[0, 0, 1],
        noise_factor=0,
        virtual_time=0.2,
    )


@pytest.mark.parametrize("kind", ["plain", "arrows", "lines"])
def test_uniform_field_color_queries_follow_its_current_color(kind: str) -> None:
    uniform = field(kind, m.RED)
    uniform.set_color(m.GREEN)
    np.testing.assert_array_equal(uniform.pos_to_rgb(np.zeros(3)), m.GREEN.to_rgb())
    assert uniform.pos_to_color(np.zeros(3)) == m.GREEN


def test_a_stream_lines_colors_run_from_its_start_to_its_end() -> None:
    lines = m.StreamLines(
        lambda p: np.array([1.0, 0.5, 0]), x_range=[-2, 2, 1], y_range=[-2, 2, 1]
    )
    for line in lines.stream_lines:  # straight: its ends are its box's corners
        np.testing.assert_allclose(
            line.get_gradient_start_and_end_points(),
            (line.get_start(), line.get_end()),
            atol=1e-9,
        )
