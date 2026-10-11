"""Number lines, axes, planes and charts put numbers where their scales say.

- A number line's `number_to_point` and `point_to_number` are inverse, on any line: any
  range, length, turn and place, linear or logarithmic; the ends of its range are the ends of
  the line, and equal steps of the range are equal steps along it (of exponents, on a
  logarithmic line). Ticks and numbers added later follow the line's attributes as they are
  then, as if it had been made with them.
- A graph of a function samples it the same however the function takes its argument: arrays
  at once, one value at a time, or arrays answered wrongly; an error the function raises
  reaches the caller.
- Axes' `coords_to_point` and `point_to_coords` are inverse, for any ranges and lengths, on
  linear and logarithmic axes alike; `c2p` and `axes @ coords` are the same map; the origin is
  where the axes cross. Their lengths are the lengths they were made with. Riemann rectangles
  span their sample and their base, on turned axes too. A line graph's vertices are its
  coordinates' points; an empty one draws nothing; its coordinates come in equal numbers.
- A plane's lines are its grid: a number plane's at every step from each axis, outward on
  each side, every `faded_line_ratio`-th a background line and the ones between faded (the
  axis's own line too, unless every line is a background one), each across the whole plane;
  a polar plane's circles at every fraction of a radius step out to its radius, and its
  radial lines at every fraction of an azimuth step from its offset, each partition starting
  with a background line. Faded lines are half as wide and opaque as the background ones.
- Each bar of a bar chart spans from 0 to its value, made with the values or changed to them.
- A sample space's divisions tile it, in either direction.
- Axes and planes fit the frame they are made in, wide, tall or square: axes given no length
  span the frame less a margin (3D axes, its short side), and planes fill it, but an axis
  given a `unit_size` and no length is that size per unit.
"""

from collections.abc import Callable, Sequence

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.strategies import angles, arrays

import manimgx as m


@st.composite
def _axis_ranges(draw: st.DrawFn) -> tuple[float, float, float]:
    low = draw(st.floats(-50, 50))
    return (low, low + draw(st.floats(0.5, 100)), draw(st.floats(0.1, 10)))


@st.composite
def lines(draw: st.DrawFn) -> m.NumberLine:
    line = m.NumberLine(
        x_range=draw(_axis_ranges()),
        length=draw(st.floats(1, 12)),
        include_tip=draw(st.booleans()),
    )
    return line.rotate(draw(angles())).shift(draw(arrays(3, 5)))


@given(line=lines(), fraction=st.floats(-0.5, 1.5))
def test_numbers_and_points_are_inverse(line: m.NumberLine, fraction: float) -> None:
    low, high = line.x_range[:2]
    number = low + fraction * (high - low)
    assert line.point_to_number(line.number_to_point(number)) == pytest.approx(
        number, abs=1e-9 * (1 + abs(number))
    )


@given(
    exponents=st.tuples(st.integers(-3, 1), st.integers(1, 4)),
    fraction=st.floats(0, 1),
    base=st.sampled_from([2, 10, np.e]),
)
def test_a_logarithmic_line_reads_its_numbers_back(
    exponents: tuple[int, int], fraction: float, base: float
) -> None:
    low, high = exponents[0], exponents[0] + exponents[1]
    line = m.NumberLine(x_range=(low, high, 1), scaling=m.LogBase(base=base))
    number = base ** (low + fraction * (high - low))
    assert line.point_to_number(line.number_to_point(number)) == pytest.approx(
        number, rel=1e-9
    )
    # equal steps of exponent are equal steps along the line
    a, b, c = (line.number_to_point(base**e) for e in (low, low + 0.5, low + 1))
    np.testing.assert_allclose(b - a, c - b, atol=1e-9)


@given(line=lines())
def test_the_ranges_ends_are_the_lines_ends(line: m.NumberLine) -> None:
    low, high = line.x_range[:2]
    start, end = line.number_to_point(np.array([low, high]))
    points = line.points
    np.testing.assert_allclose(start, points[0], atol=1e-9)
    if not line.has_tip():
        np.testing.assert_allclose(end, points[-1], atol=1e-9)


def test_ticks_and_numbers_added_later_follow_the_lines_attributes() -> None:
    line = m.NumberLine((0, 3, 1), include_ticks=False, numbers_to_exclude=[0.0])
    line.font_size = 27
    line.label_direction = m.UP
    line.tick_size = 0.2
    line.numbers_with_elongated_ticks = [1.0]
    line.add_numbers()
    line.add_ticks()
    made = m.NumberLine(
        (0, 3, 1),
        numbers_to_exclude=[0.0],
        font_size=27,
        label_direction=m.UP,
        tick_size=0.2,
        numbers_with_elongated_ticks=[1.0],
        include_numbers=True,
    )
    for added, like in ((line.numbers, made.numbers), (line.ticks, made.ticks)):
        parts, wanted = added.get_family(), like.get_family()
        assert len(parts) == len(wanted) > 1
        for part, other in zip(parts, wanted, strict=True):
            np.testing.assert_array_equal(part.points, other.points)
    for number, value in zip(line.numbers, (1, 2, 3), strict=True):  # (and as asked)
        assert isinstance(number, m.DecimalNumber)
        assert number.get_value() == value
        assert number.font_size == pytest.approx(27)
        assert number.get_bottom()[1] > line.n2p(value)[1]
    assert [tick.height for tick in line.ticks] == pytest.approx([0.4, 0.8, 0.4, 0.4])
    assert line.get_unit_vector()[0] == pytest.approx(line.unit_size)


FUNCTIONS: dict[str, Callable[[float], float]] = {
    "a square": lambda t: t * t,
    "a wave": lambda t: np.sin(3 * t) + t,
    "a constant": lambda t: 2.0,  # (one value, an array or not)
}


def one_at_a_time(function: Callable[[float], float]) -> Callable[[float], float]:
    def scalar(t: float) -> float:
        if isinstance(t, np.ndarray):
            raise TypeError("one value at a time")
        return function(t)

    return scalar


def wrong_for_arrays(function: Callable[[float], float]) -> Callable[[float], float]:
    def wrong(t: float) -> float:
        return function(t) + 1 if isinstance(t, np.ndarray) else function(t)

    return wrong


FORMS: dict[str, Callable[[Callable[[float], float]], Callable[[float], float]]] = {
    "taking arrays": lambda function: function,
    "taking one value at a time": one_at_a_time,
    "answering arrays wrongly": wrong_for_arrays,
}


@given(
    function=st.sampled_from(sorted(FUNCTIONS)),
    form=st.sampled_from(sorted(FORMS)),
    low=st.floats(-3, 0),
    span=st.floats(0.5, 4),
    step=st.sampled_from([0.05, 0.1, 0.25]),
)
def test_a_graph_samples_its_function_however_it_takes_its_argument(
    function: str, form: str, low: float, span: float, step: float
) -> None:
    f = FUNCTIONS[function]
    x_range = (low, low + span, step)
    graph = m.FunctionGraph(FORMS[form](f), x_range=x_range)
    xs = [*map(float, np.arange(*x_range)), x_range[1]]  # (every step, and the end)
    samples = np.vstack([graph.get_start_anchors(), graph.get_end_anchors()[-1:]])
    np.testing.assert_allclose(
        samples, [(x, f(x), 0) for x in xs], rtol=1e-9, atol=1e-12
    )


def test_an_error_the_function_raises_reaches_the_caller() -> None:
    def fail(t: float) -> float:
        if t < 0:
            raise ValueError("negative parameter")
        return t

    with pytest.raises(ValueError, match="negative parameter"):
        m.FunctionGraph(fail, x_range=(-1, 1, 0.1))


@st.composite
def _coordinate_ranges(draw: st.DrawFn) -> tuple[float, float, float]:
    low = draw(st.floats(-50, 50))
    return (low, low + draw(st.floats(0.5, 100)), draw(st.floats(0.1, 10)))


@given(
    x=_coordinate_ranges(),
    y=_coordinate_ranges(),
    fx=st.floats(0, 1),
    fy=st.floats(0, 1),
    lengths=st.tuples(st.floats(1, 12), st.floats(1, 7)),
)
def test_coordinates_and_points_are_inverse(
    x: tuple[float, float, float],
    y: tuple[float, float, float],
    fx: float,
    fy: float,
    lengths: tuple[float, float],
) -> None:
    axes = m.Axes(x_range=x, y_range=y, x_length=lengths[0], y_length=lengths[1])
    coords = (x[0] + fx * (x[1] - x[0]), y[0] + fy * (y[1] - y[0]))
    point = axes.coords_to_point(*coords)
    np.testing.assert_allclose(
        axes.point_to_coords(point)[:2], coords, atol=1e-8 * (1 + np.abs(coords).max())
    )
    np.testing.assert_array_equal(axes.c2p(*coords), point)
    np.testing.assert_array_equal(axes @ coords, point)


@given(fx=st.floats(0, 1), fy=st.floats(0, 1))
def test_a_logarithmic_axis_reads_its_coordinates_back(fx: float, fy: float) -> None:
    axes = m.Axes(
        x_range=(0, 10, 1), y_range=(-2, 3, 1), y_axis_config={"scaling": m.LogBase()}
    )
    coords = (10 * fx, 10 ** (-2 + 5 * fy))
    back = axes.point_to_coords(axes.coords_to_point(*coords))
    assert back[0] == pytest.approx(coords[0], abs=1e-9)
    assert back[1] == pytest.approx(coords[1], rel=1e-9)


@given(x=_coordinate_ranges(), y=_coordinate_ranges())
def test_the_origin_is_where_the_axes_cross(
    x: tuple[float, float, float], y: tuple[float, float, float]
) -> None:
    axes = m.Axes(x_range=x, y_range=y)
    if x[0] <= 0 <= x[1] and y[0] <= 0 <= y[1]:
        np.testing.assert_allclose(
            axes.get_origin(), axes.coords_to_point(0, 0), atol=1e-9
        )


def test_length_properties_remain_construction_lengths() -> None:
    axes = m.ThreeDAxes(x_length=6, y_length=4, z_length=2)
    lengths = axes.x_length, axes.y_length, axes.z_length
    axes.scale(2)
    assert (axes.x_length, axes.y_length, axes.z_length) == lengths
    np.testing.assert_allclose(lengths, [6, 4, 2], atol=1e-12)


@pytest.mark.parametrize(
    ("sample", "offset"), [("left", 0), ("center", 0.5), ("right", 1)]
)
@pytest.mark.parametrize("bounded", [False, True])
def test_riemann_rectangles_span_their_sample_and_base_on_transformed_axes(
    sample: str, offset: float, bounded: bool
) -> None:
    axes = m.Axes(x_range=(-2, 2), y_range=(-2, 3), tips=False)
    axes.rotate(0.31, axis=(1, 2, 3)).scale(1.3).shift((1.1, -2.3, 0.4))
    graph = axes.plot(lambda x: x * x - 0.25, x_range=(-1, 1, 0.5))
    lower = axes.plot(lambda x: 0.2 * x + 0.1, x_range=(-1, 1, 0.5))
    rectangles = axes.get_riemann_rectangles(
        graph,
        x_range=(-1, 1),
        dx=1,
        input_sample_type=sample,
        bounded_graph=lower if bounded else None,
        fill_opacity=0.4,
        stroke_width=2.5,
    )
    assert len(rectangles) == 2
    for x, rectangle in zip((-1, 0), rectangles, strict=True):
        base = 0.2 * x + 0.1 if bounded else 0
        points = np.array(
            [
                axes.c2p(x, base),
                axes.c2p(x + 1.001, base),
                axes.c2p(x + offset, (x + offset) ** 2 - 0.25),
            ]
        )
        low, high = points.min(axis=0), points.max(axis=0)
        np.testing.assert_allclose(
            [rectangle.get_left()[0], rectangle.get_right()[0]],
            [low[0], high[0]],
            atol=1e-12,
        )
        np.testing.assert_allclose(
            [rectangle.get_bottom()[1], rectangle.get_top()[1]],
            [low[1], high[1]],
            atol=1e-12,
        )
        assert rectangle.get_center()[2] == pytest.approx((low[2] + high[2]) / 2)
        np.testing.assert_array_equal(rectangle.paint.fill[:, 3], 0.4)
        assert rectangle.stroke_width == 2.5


@pytest.mark.parametrize("kind", [m.Axes, m.NumberPlane, m.ThreeDAxes])
@pytest.mark.parametrize("dots", [False, True])
def test_empty_line_graph_is_an_empty_drawing(kind: type[m.Axes], dots: bool) -> None:
    graph = kind().plot_line_graph([], [], add_vertex_dots=dots)
    assert graph["line_graph"].points.shape == (0, 3)
    assert not graph.has_points()
    if dots:
        assert len(graph["vertex_dots"]) == 0
    assert not graph.copy().family_members_with_points()


@pytest.mark.parametrize("sizes", [(1, 3, 3), (3, 1, 3), (3, 3, 1), (0, 1, 0)])
def test_line_graph_requires_equal_lengths_even_for_unused_z(
    sizes: tuple[int, int, int],
) -> None:
    x, y, z = sizes
    with pytest.raises(ValueError, match=r"shape|zip"):
        m.Axes().plot_line_graph(range(x), range(y), range(z))


@pytest.mark.parametrize("kind", [m.Axes, m.ThreeDAxes])
@pytest.mark.parametrize("logarithmic", [False, True])
def test_line_graph_matches_independent_scalar_coordinates(
    kind: type[m.Axes], logarithmic: bool
) -> None:
    axes = kind(
        x_range=(-1, 2),
        y_range=(-2, 1),
        axis_config=(
            {"scaling": m.LogBase(custom_labels=False)} if logarithmic else None
        ),
    )
    axes.shift([0.7, -0.3, 0.4]).rotate(0.23, axis=[1, 2, 3]).stretch(-1.1, 1)
    values = np.geomspace(0.1, 7, 17) if logarithmic else np.linspace(-1.3, 2.7, 17)
    ys, zs = values * 0.2, values * 0.7
    vertices = [
        axes.coords_to_point(x, y, z) for x, y, z in zip(values, ys, zs, strict=True)
    ]
    expected = m.VMobject().set_points_as_corners(vertices)
    graph = axes.plot_line_graph(
        map(float, values),
        map(float, ys),
        map(float, zs),
        vertex_dot_radius=0.13,
        vertex_dot_style={"color": m.GREEN},
    )
    np.testing.assert_array_equal(graph["line_graph"].points, expected.points)
    for dot, vertex in zip(graph["vertex_dots"], vertices, strict=True):
        np.testing.assert_array_equal(
            dot.points, m.Dot(vertex, radius=0.13, color=m.GREEN).points
        )


def grid(
    low: float, high: float, step: float, ratio: int
) -> tuple[list[float], list[float]]:
    """A number plane's background and faded lines along an axis, by coordinate: the axis's
    own line, then every `step / ratio` outward on each side, within the range."""
    fine = step / ratio
    background: list[float] = []
    faded: list[float] = []
    (background if ratio == 1 else faded).append(0.0)
    for sign, bound in ((1, high), (-1, -low)):
        k = 1
        while k * fine < bound - 1e-9:
            (background if k % ratio == 0 else faded).append(sign * k * fine)
            k += 1
    return background, faded


NUMBER_PLANES = [
    pytest.param((-4, 4, 3), (-4, 4, 3), 3, id="thirds, restarting at the axis"),
    pytest.param((-3.25, 3.25, 1), (-2.25, 2.75, 1), 2, id="halves"),
    pytest.param((-2.5, 3.5, 1), (-1.5, 1.5, 0.5), 1, id="every line a background one"),
    pytest.param((-1.75, 5.5, 2), (-6.4, 0.6, 0.5), 4, id="quarters, lopsided"),
    pytest.param((-1, 1, 1), (-1, 1, 1), 3, id="thirds, to the edge"),
]


@pytest.mark.parametrize(("x_range", "y_range", "ratio"), NUMBER_PLANES)
def test_a_number_planes_lines_are_its_grid(
    x_range: tuple[float, float, float], y_range: tuple[float, float, float], ratio: int
) -> None:
    plane = m.NumberPlane(x_range=x_range, y_range=y_range, faded_line_ratio=ratio)
    across = len(plane.x_lines)  # (the faded lines: across, then up)
    faded_across = len(grid(*y_range, ratio)[1])
    for lines, faded, axis, along in (
        (plane.x_lines, plane.faded_lines[:faded_across], 1, x_range),
        (plane.y_lines, plane.faded_lines[faded_across:], 0, y_range),
    ):
        expected = grid(*(y_range if axis else x_range), ratio)
        for group, places in zip((lines, faded), expected, strict=True):
            ends = [plane.point_to_coords(line.get_start_and_end()) for line in group]
            np.testing.assert_allclose(
                [e[:, axis] for e in ends], [[p, p] for p in places], atol=1e-9
            )
            for start, end in ends:  # (across the whole plane)
                assert sorted((start[1 - axis], end[1 - axis])) == pytest.approx(
                    along[:2]
                )
    assert list(plane.background_lines) == [*plane.x_lines, *plane.y_lines]
    assert len(plane.x_lines) == across


POLAR_PLANES = [
    pytest.param(3, 3, 4, 3, 0, id="thirds"),
    pytest.param(2, 1, 8, 2, 0.3, id="halves, turned"),
    pytest.param(2, 0.5, 4, 4, 0, id="quarters"),
    pytest.param(1.5, 0.5, 2, 1, 0, id="every line a background one"),
    pytest.param(2, 1, 4, 3, 0, id="thirds of two steps"),
    pytest.param(1, 1, 3, 3, 0, id="thirds of a third of a turn"),
    pytest.param(2.5, 1, 4, 1, 0, id="a radius between circles"),
]


@pytest.mark.parametrize(
    ("radius", "radius_step", "azimuth_step", "ratio", "offset"), POLAR_PLANES
)
def test_a_polar_planes_lines_are_its_grid(
    radius: float, radius_step: float, azimuth_step: int, ratio: int, offset: float
) -> None:
    plane = m.PolarPlane(
        radius_max=radius,
        radius_step=radius_step,
        azimuth_step=azimuth_step,
        azimuth_offset=offset,
        faded_line_ratio=ratio,
    )
    unit = plane.x_axis.get_unit_vector()[0]
    fine = radius_step / ratio
    radii = [k * fine for k in range(int(radius / fine + 1e-9) + 1)]  # (to the radius)
    turns = [
        offset + k * m.TAU / (azimuth_step * ratio) for k in range(azimuth_step * ratio)
    ]
    for group, main in ((plane.background_lines, True), (plane.faded_lines, False)):
        circles = [line for line in group if isinstance(line, m.Circle)]
        rays = [line for line in group if not isinstance(line, m.Circle)]
        wanted = [r for k, r in enumerate(radii) if (k % ratio == 0) == main]
        np.testing.assert_allclose(
            [c.width / 2 / unit for c in circles], wanted, atol=1e-9
        )
        wanted = [a for k, a in enumerate(turns) if (k % ratio == 0) == main]
        assert len(rays) == len(wanted)
        for ray, turn in zip(rays, wanted, strict=True):
            start, end = ray.get_start_and_end()
            np.testing.assert_allclose(start, plane.get_origin(), atol=1e-9)
            direction = (end - start) / np.linalg.norm(end - start)
            np.testing.assert_allclose(
                direction[:2], [np.cos(turn), np.sin(turn)], atol=1e-9
            )


@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1920), (1000, 1000)])
def test_a_plane_fills_the_frame_it_is_made_in(size: tuple[int, int]) -> None:
    # the frame as the scene's file sets it, after ManimGX is imported: wide, tall, square
    m.config.pixel_width, m.config.pixel_height = size
    w, h = m.config.frame_x_radius, m.config.frame_y_radius
    plane = m.NumberPlane()
    np.testing.assert_allclose(plane.c2p(-w, -h), [-w, -h, 0], atol=1e-9)
    np.testing.assert_allclose(plane.c2p(w, h), [w, h, 0], atol=1e-9)
    np.testing.assert_allclose([*plane.x_range[:2], *plane.y_range[:2]], [-w, w, -h, h])
    assert m.PolarPlane().width == pytest.approx(2 * min(w, h))


@pytest.mark.parametrize(
    ("size", "lengths"),
    [((1920, 1080), (12, 6)), ((1080, 1920), (6, 12)), ((1000, 1000), (6, 6))],
)
def test_axes_fit_the_frame_they_are_made_in(
    size: tuple[int, int], lengths: tuple[float, float]
) -> None:
    # the frame as the scene's file sets it, after ManimGX is imported: wide, tall, square
    m.config.pixel_width, m.config.pixel_height = size
    axes = m.Axes()
    assert (axes.x_length, axes.y_length) == pytest.approx(lengths)
    # 3D axes take the frame's short side, which these frames share
    three_d = m.ThreeDAxes()
    assert (three_d.x_length, three_d.y_length, three_d.z_length) == pytest.approx(
        (10.5, 10.5, 6.5)
    )


def test_an_axis_given_a_unit_size_and_no_length_is_that_size_per_unit() -> None:
    axes = m.Axes(x_range=[0, 10, 1], x_axis_config={"unit_size": 0.5})
    assert axes.x_length == pytest.approx(5)
    assert axes.y_length == pytest.approx(6)  # the other axis fits the frame
    # a length given wins
    axes = m.Axes(x_length=7, x_axis_config={"unit_size": 0.5})
    assert axes.x_length == pytest.approx(7)
    # and a plane's unit is a scene unit unless one is given
    plane = m.NumberPlane(x_range=[-2, 2, 1], axis_config={"unit_size": 2})
    assert plane.x_length == pytest.approx(8)


def test_a_planes_faded_lines_halve_each_of_several_opacities() -> None:
    # an opacity can be one for each part of a stroke: each is halved
    plane = m.NumberPlane(
        faded_line_ratio=2, background_line_style={"stroke_opacity": [1.0, 0.5]}
    )
    full = plane.background_lines[0].get_stroke_opacity()
    assert len(plane.faded_lines) > 0
    for line in plane.faded_lines:
        assert line.get_stroke_opacity() == pytest.approx(full * 0.5)


@pytest.mark.parametrize("plane_type", [m.NumberPlane, m.ComplexPlane, m.PolarPlane])
def test_plane_faded_lines_use_half_the_background_width_and_opacity(
    plane_type: type[m.NumberPlane] | type[m.PolarPlane],
) -> None:
    plane = plane_type(
        faded_line_ratio=3,
        background_line_style={
            "stroke_color": m.GREEN,
            "stroke_width": 3.2,
            "stroke_opacity": 0.7,
            "fill_opacity": 0.4,
        },
    )
    for group, factor in ((plane.background_lines, 1.0), (plane.faded_lines, 0.5)):
        assert len(group) > 0
        for line in group:
            assert line.get_stroke_color() == m.GREEN
            assert line.get_stroke_width() == 3.2 * factor
            assert line.get_stroke_opacity() == 0.7 * factor
            assert line.get_fill_opacity() == 0.4 * factor


values = st.lists(st.integers(-10, 10), min_size=2, max_size=8)


def assert_bars_show(chart: m.BarChart, shown: Sequence[float]) -> None:
    for bar, value in zip(chart.bars, shown, strict=True):
        low, high = sorted((0, value))
        np.testing.assert_allclose(
            [bar.get_bottom()[1], bar.get_top()[1]],
            [chart.c2p(0, low)[1], chart.c2p(0, high)[1]],
            atol=1e-9,
        )


@given(before=values, data=st.data())
def test_each_bar_spans_from_zero_to_its_value(
    before: list[int], data: st.DataObject
) -> None:
    chart = m.BarChart(before, y_range=[-10, 10, 2])
    assert_bars_show(chart, before)
    after = data.draw(
        st.lists(st.integers(-10, 10), min_size=len(before), max_size=len(before))
    )
    chart.change_bar_values(after)
    assert_bars_show(chart, after)


@pytest.mark.parametrize("dim", [0, 1])
@pytest.mark.parametrize("reverse", [False, True])
def test_division_parts_tile_the_parent_in_either_direction(
    dim: int, reverse: bool
) -> None:
    space = m.SampleSpace(width=5, height=3).shift(m.LEFT + m.UP)
    direction = (m.RIGHT if dim == 0 else m.UP) * (-1 if reverse else 1)
    parts = space.get_division_along_dimension(
        (0.2, 0.3), dim, [m.RED, m.BLUE], direction
    )
    assert not space.submobjects
    assert len(parts) == 3
    last_point = space.get_critical_point(-direction)
    for part, fraction in zip(parts, [0.2, 0.3, 0.5], strict=True):
        assert isinstance(part, m.SampleSpace)
        assert part.length_over_dim(dim) == pytest.approx(
            space.length_over_dim(dim) * fraction
        )
        np.testing.assert_allclose(
            part.get_critical_point(-direction), last_point, atol=1e-12
        )
        last_point = part.get_critical_point(direction)
    np.testing.assert_allclose(
        last_point, space.get_critical_point(direction), atol=1e-12
    )
