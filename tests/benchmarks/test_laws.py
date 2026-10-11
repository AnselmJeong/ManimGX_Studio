"""What things cost grows as they do: no count of work grows faster than what is made.

Each law compares two runs in one process: no number is pinned, and every machine checks it
the same, since work (counted by `tests.benchmarks.work`) is the same everywhere. Each run
starts from nothing remembered and is run once before it is counted, so it pays for its own
work only: not for its first run's (imports, layouts, prototypes), nor for what another run
left in ManimGX's memories or flushed from them.

- **Growth.** Made twice as big, a thing costs at most twice the work (a surface of twice the
  resolution, four times): a path built curve by curve, a group of shapes played, a text
  written, a paragraph or a line of code set, a graph redrawn every frame over wider axes, a
  surface raised and turned, a path traced for longer, a film held for longer, a table laid
  out (a row or a column of it too), a plane of more lines, a member removed from deeper in a
  tree, a family listed or emptied however many paths reach its members, shapes matched to
  shapes, an instant of a mobject with more updaters. Some cost Python nothing more as they
  grow (their arrays do the growing): a regular polygon's vertices, curves refined into as many
  or three times as many, a cloud's line, a line graph, rounded corners, a polygram, a sphere,
  cone, cylinder or torus at a finer resolution; a function graph calls Python no more often
  sampled more finely; and a point on a busier number line, or dashing equal curves again,
  costs nothing more at all. A pole searched for three times as finely costs at most three
  times the work (it refines the cells near the best, never the whole area: nine times). The
  largest size always runs, where growth shows most; Hypothesis draws others and `target`
  climbs toward the worst ratio.
- **Sharing.** Copies of any mobject, moved, turned and scaled, upload what one does: a shape
  is uploaded once, and its copies and moves are placements of it.
- **Stillness.** A scene that holds any mobject still (one with no updater) costs as much for
  half a minute as for a second: its held frames are one frame, shown longer.
- **History.** A story told four times costs twice what two tellings do: nothing a scene keeps
  makes its later frames dearer.
- **Restating.** Assigning any mobject the points, colors and triangles it holds computes,
  hashes and uploads nothing, once or every frame: all that was made of them stands.
- **Remembering.** A construction ManimGX remembers (an SVG, a text, a formula), made again,
  computes nothing again.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import fields

import numpy as np
import pytest
from hypothesis import assume, example, given, reject, settings, target
from hypothesis import strategies as st
from tests.benchmarks.work import Work, count
from tests.scenes import SHAPES, Story, scene, stories
from tests.strategies import MOBJECTS, angles

import manimgx as m
from manimgx import caches
from manimgx.animation import clock
from manimgx.config import config
from manimgx.drawing.geometry import bezier_remap

SLACK = 0.1
"""A law's allowance over proportion, for what a thing's fixed costs and manimgx's memories
leave uneven between two runs (a paint remembers the paints made from it, and `caches.clear`
does not forget those)."""
COUNTS = tuple(f.name for f in fields(Work))
PYTHON = {"calls": 0, "loops": 0}
"""The power of a law whose Python work does not grow at all: no loop runs once an element."""

type Run = Callable[[], object]


def render(construct: Callable[[m.Scene], None]) -> Run:
    """A run that tells `construct` as a scene at 10 fps, its frames counted, not drawn."""

    def run() -> None:
        clock.reset()
        config.frame_rate = 10
        scene(construct).render()

    return run


def growth(small: Work, large: Work) -> dict[str, float]:
    """Each count's growth: the larger run's over the smaller's (a count both leave at 0 did
    not grow)."""
    out = {}
    for f in fields(Work):
        a, b = getattr(small, f.name), getattr(large, f.name)
        out[f.name] = b / a if a else (1.0 if b == 0 else math.inf)
    return out


def measured(make: Callable[[], Run]) -> Work:
    """The work of the run `make` sets up (the setting up uncounted), from nothing
    remembered (`caches.clear`) and once before it is counted: a run pays only for its own
    work, never for what another left in, or flushed from, ManimGX's memories."""
    caches.clear()
    make()()  # what a first run pays once: imports, layouts, prototypes
    return count(make())[1]


def law(
    build: Callable[[int], Run],
    sizes: tuple[int, int],
    power: int | Mapping[str, int] = 1,
) -> Callable[..., None]:
    """The growth law for the run `build(n)` sets up, at sizes in `sizes`: its work grows as
    the size to `power`, every count's, or each count's named (`PYTHON`)."""
    powers = power if isinstance(power, Mapping) else dict.fromkeys(COUNTS, power)
    bounds = {k: 2**p * (1 + SLACK) for k, p in powers.items()}

    def test(n: int) -> None:
        small = measured(lambda: build(n))
        large = measured(lambda: build(2 * n))
        assert small.calls, "no work of manimgx's was counted: the law proves nothing"
        grown = growth(small, large)
        worst = max(bounds, key=lambda k: grown[k] / bounds[k])
        target(min(grown[worst], 1e6) / bounds[worst], label="growth over the bound")
        assert grown[worst] <= bounds[worst], (
            f"at size {2 * n}, {grown[worst]:.2f}x the {worst} of size {n} (at most "
            f"{bounds[worst]:.2f}x): {small} → {large}"
        )

    # a name of its own, before Hypothesis wraps it: its database and its derandomized
    # draws are keyed by the function's name and source
    test.__name__ = test.__qualname__ = f"test_{getattr(build, '__name__', 'law')}"
    test.__doc__ = build.__doc__
    return settings(max_examples=10)(
        given(st.integers(*sizes))(example(sizes[1])(test))
    )


def path(n: int) -> Run:
    """A path of `n` segments, built curve by curve, then drawn."""
    corners = [[k / n, math.sin(7 * k / n), 0.0] for k in range(n + 1)]

    def construct(scene: m.Scene) -> None:
        built = m.VMobject().start_new_path(corners[0])
        for corner in corners[1:]:
            built.add_line_to(corner)
        scene.play(m.Create(built))

    return render(construct)


def group(n: int) -> Run:
    """`n` of each shape, faded in one after another, then moved, recolored and turned
    together, in plays that last as long whatever `n` is."""

    def construct(scene: m.Scene) -> None:
        shapes = m.VGroup(*(SHAPES[s]() for s in sorted(SHAPES) * n)).arrange_in_grid()
        scene.play(m.LaggedStart(*(m.FadeIn(s) for s in shapes), run_time=2))
        scene.play(shapes.animate.shift(m.UP).set_color(m.RED))
        scene.play(m.Transform(shapes, shapes.copy().rotate(1.0)))

    return render(construct)


def text(n: int) -> Run:
    """A text of `n` words, written."""
    words = " ".join(["manimgx"] * n)

    def construct(scene: m.Scene) -> None:
        scene.play(m.Write(m.Text(words, font_size=12).scale_to_fit_width(12)))

    return render(construct)


def plot(n: int) -> Run:
    """Axes `n` units wide, and a graph over them redrawn every frame (up to 12 units, whose
    graph's anchors stay under `bezier._SMOOTHING_UP_TO`: past it, smoothing solves in a loop
    instead of applying a cached map, another algorithm)."""

    def construct(scene: m.Scene) -> None:
        axes = m.Axes(x_range=[0, n, 1], y_range=[-1, 1, 0.5])
        k = m.ValueTracker(1.0)
        graph = m.always_redraw(
            lambda: axes.plot(lambda x: math.sin(k.get_value() * x))
        )
        scene.add(axes, graph)
        scene.play(k.animate.set_value(2.0))

    return render(construct)


def surface(n: int) -> Run:
    """A surface of resolution `n` by `n`, raised by an updater and turned."""

    def construct(scene: m.Scene) -> None:
        s = m.Surface(
            lambda u, v: np.array([u, v, math.sin(u) * math.cos(v)]),
            u_range=[-2, 2],
            v_range=[-2, 2],
            resolution=(n, n),
        )
        k = m.ValueTracker(0.0)
        s.add_updater(lambda mob: mob.set_z(k.get_value()))
        scene.add(s)
        scene.play(k.animate.set_value(1.0), m.Rotate(s, 1.0))

    return render(construct)


def trace(n: int) -> Run:
    """A dot going round for `n` seconds, its path traced."""

    def construct(scene: m.Scene) -> None:
        dot = m.Dot().shift(m.RIGHT)
        scene.add(dot, m.TracedPath(dot.get_center))
        scene.play(m.Rotate(dot, n * math.tau, about_point=m.ORIGIN, run_time=n))

    return render(construct)


def held(n: int) -> Run:
    """A film `n` seconds long of a turning square and a digit counting tenths."""

    def construct(scene: m.Scene) -> None:
        square = m.Square()
        square.add_updater(lambda mob, dt: mob.rotate(dt))
        digit = m.Integer(0).add_updater(
            lambda i: i.set_value(int(10 * clock.now) % 10)
        )
        scene.add(square, digit)
        scene.wait(n)

    return render(construct)


def table(n: int) -> Run:
    """A table of n by n entries, laid out with lines between its cells."""
    return lambda: m.MobjectTable([[m.Square(0.2) for _ in range(n)] for _ in range(n)])


def polygon(n: int) -> Run:
    """The vertices of a regular polygon of `n` sides."""
    return lambda: m.regular_vertices(n)


def refine(n: int, factor: int = 1) -> Run:
    """`n` equal curves refined into `factor` times as many."""
    curves = np.tile(m.Line().points[None], (n, 1, 1))
    return lambda: bezier_remap(curves, factor * n)


def refine_threefold(n: int) -> Run:
    """`n` equal curves refined into three times as many."""
    return refine(n, 3)


def dash(n: int) -> Run:
    """A path of `n` equal lines dashed again: its curves were measured when it was first."""
    path = m.VMobject().set_points(np.tile(m.Line().points, (n, 1)))
    m.DashedVMobject(path)
    return lambda: m.DashedVMobject(path)


def removal(n: int) -> Run:
    """A member removed from `n` levels down a tree in a scene."""
    leaf = m.Mobject()
    tree = leaf
    for _ in range(n):
        tree = m.Group(m.Mobject(), tree, m.Mobject())
    world = m.Scene().add(tree)
    return lambda: world.remove(leaf)


def diamond(n: int) -> m.Mobject:
    """`n` levels of a diamond: each level's two groups hold the one below, so the paths to
    its bottom double a level, its members only add three."""
    root = m.Mobject()
    for _ in range(n):
        left, right, parent = (m.Group() for _ in range(3))
        left.submobjects = [root]
        right.submobjects = [root]
        parent.submobjects = [left, right]
        root = parent
    return root


def family(n: int) -> Run:
    """The family of a diamond `n` levels deep, listed."""
    root = diamond(n)

    def run() -> None:
        assert len(root.get_family()) == 3 * n + 1

    return run


def emptying(n: int) -> Run:
    """A scene of a diamond `n` levels deep, emptied by removing its bottom."""
    root = diamond(n)
    leaf = root.get_family()[-1]
    world = m.Scene()
    world.mobjects = [root]

    def run() -> None:
        world.remove(leaf)
        assert world.mobjects == []

    return run


def matching(n: int) -> Run:
    """`n` squares and `n` circles matched by shape onto the same, moved."""

    def construct(scene: m.Scene) -> None:
        shapes = m.VGroup(
            *(m.Square() for _ in range(n)), *(m.Circle() for _ in range(n))
        ).arrange()
        scene.play(m.TransformMatchingShapes(shapes, shapes.copy().shift(m.UP)))

    return render(construct)


def updating(n: int) -> Run:
    """A dot with `n` updaters, waiting a second: each instant walks its list once."""

    def construct(scene: m.Scene) -> None:
        dot = m.Dot()
        for _ in range(n):
            dot.add_updater(lambda mob, dt: None)
        scene.add(dot)
        scene.wait(1)

    return render(construct)


U = [[0, 0, 0], [2, 0, 0], [2, 2, 0], [1.5, 2, 0], [1.5, 0.5, 0],
     [0.5, 0.5, 0], [0.5, 2, 0], [0, 2, 0], [0, 0, 0]]  # fmt: skip


def rectangle_pole(n: int) -> Run:
    """A 32-by-2 rectangle's pole, to a precision of 1/n: its first cells hold it."""
    rectangle = [[0, 0, 0], [32, 0, 0], [32, 2, 0], [0, 2, 0], [0, 0, 0]]
    return lambda: m.polylabel([rectangle], precision=1 / n)


def line_cloud(n: int) -> Run:
    """A point cloud's line, `n` points to the unit: its points an array's, its Python
    work the same however many."""
    cloud = m.Mobject1D(density=n)
    return lambda: cloud.add_line(m.ORIGIN, m.RIGHT)


def ring_cloud(n: int) -> Run:
    """A cloud dot of density `n`: n rings, n² points; its Python work grows with the rings."""
    return lambda: m.PointCloudDot(radius=1, density=n)


def code(n: int) -> Run:
    """Code of one line `n` characters wide."""
    return lambda: m.Code(code_string="H" * n, add_line_numbers=False)


def row_table(n: int) -> Run:
    """A table of one row of `n` dots, its lines inside and out."""
    return lambda: m.MobjectTable(
        [[m.Dot() for _ in range(n)]], include_outer_lines=True
    )


def column_table(n: int) -> Run:
    """A table of one column of `n` dots, its lines inside and out."""
    return lambda: m.MobjectTable(
        [[m.Dot()] for _ in range(n)], include_outer_lines=True
    )


def annotated(n: int) -> Run:
    """A number line's point for a number, the line carrying `n` members of no concern to
    it."""
    line = m.NumberLine(include_ticks=False, include_tip=True)
    line.add(*(m.Mobject() for _ in range(n)))
    return lambda: line.n2p(0.37)


def graphed(n: int) -> Run:
    """The graph of a function that takes arrays, sampled at `n` points: the function
    (ManimGX's, so its calls count) called on them at once (the smoothing of the samples
    loops over them)."""
    return lambda: m.FunctionGraph(
        lambda t: m.interpolate(0.0, 2.0, t), x_range=(0, 1, 1 / n)
    )


def plotted(n: int) -> Run:
    """A line graph of `n` vertices, on axes."""
    axes = m.Axes()
    xs = np.linspace(-1, 1, n)
    return lambda: axes.plot_line_graph(xs, xs, add_vertex_dots=False)


def plotted_in_space(n: int) -> Run:
    """A line graph of `n` vertices, on spatial axes."""
    axes = m.ThreeDAxes()
    xs = np.linspace(-1, 1, n)
    return lambda: axes.plot_line_graph(xs, xs, add_vertex_dots=False)


def plane(n: int) -> Run:
    """A number plane `2n` units wide."""
    return lambda: m.NumberPlane(x_range=(-n, n), y_range=(-1, 1))


def polar(n: int) -> Run:
    """A polar plane of `n` circles."""
    return lambda: m.PolarPlane(radius_max=n, azimuth_step=4)


def rounded(n: int) -> Run:
    """A square's corners rounded, each arc drawn through `n` anchors."""
    return lambda: m.Square(2).round_corners(0.25, components_per_rounded_corner=n)


def polygram(n: int) -> Run:
    """A polygram of `n` vertices given as an array."""
    vertices = np.arange(n * 3, dtype=float).reshape(n, 3)
    return lambda: m.Polygram(vertices)


def sphere(n: int) -> Run:
    """A sphere at resolution `n`: its grid sampled at once."""
    return lambda: m.Sphere(resolution=n)


def cone(n: int) -> Run:
    """A cone at resolution `n`: its grid sampled at once."""
    return lambda: m.Cone(resolution=n)


def cylinder(n: int) -> Run:
    """A cylinder at resolution `n`: its grid sampled at once."""
    return lambda: m.Cylinder(resolution=n)


def torus(n: int) -> Run:
    """A torus at resolution `n`: its grid sampled at once."""
    return lambda: m.Torus(resolution=n)


def paragraph(n: int) -> Run:
    """A paragraph of two lines `n` characters long."""
    return lambda: m.Paragraph("H" * n, "H" * n)


test_a_path_grows_as_its_curves = law(path, (2, 200))
test_a_group_grows_as_its_members = law(group, (2, 16))
test_a_text_grows_as_its_words = law(text, (2, 24))
test_a_redrawn_graph_grows_as_its_axes = law(plot, (2, 12))
test_a_surface_grows_as_its_resolution_squared = law(surface, (4, 16), power=2)
test_a_traced_path_grows_as_its_time = law(trace, (1, 4))
test_a_film_grows_as_its_time = law(held, (1, 6))
test_a_table_grows_as_its_cells = law(table, (2, 12), power=2)
test_a_polygons_vertices_cost_python_nothing_more = law(polygon, (8, 256), PYTHON)
test_refining_curves_costs_python_nothing_more = law(refine, (8, 256), PYTHON)
test_refining_threefold_costs_python_nothing_more = law(
    refine_threefold, (8, 256), PYTHON
)
test_dashing_equal_curves_again_costs_nothing_more = law(dash, (8, 64), power=0)
test_a_removal_grows_as_its_depth = law(removal, (4, 100))
test_a_family_grows_as_its_members = law(family, (4, 8))
test_emptying_a_family_grows_as_its_members = law(emptying, (4, 8))
test_a_matching_grows_as_its_parts = law(matching, (2, 32))
test_an_instant_grows_as_its_updaters = law(updating, (2, 64))
test_a_rectangles_pole_costs_nothing_more_finer = law(
    rectangle_pole, (20, 100), power=0
)
test_a_line_cloud_costs_python_nothing_more = law(line_cloud, (32, 1024), PYTHON)
test_a_cloud_dots_python_grows_as_its_rings = law(
    ring_cloud, (8, 64), {"calls": 1, "loops": 1}
)
test_code_grows_as_its_width = law(code, (4, 64))
test_a_row_table_grows_as_its_cells = law(row_table, (8, 64))
test_a_column_table_grows_as_its_cells = law(column_table, (8, 64))
test_a_lines_point_costs_nothing_more_on_a_busier_line = law(annotated, (16, 256), 0)
test_a_function_graph_calls_python_no_more_finely = law(
    graphed, (64, 1024), {"calls": 0}
)
test_a_line_graph_costs_python_nothing_more = law(plotted, (64, 512), PYTHON)
test_a_spatial_line_graph_costs_python_nothing_more = law(
    plotted_in_space, (64, 512), PYTHON
)
test_a_plane_grows_as_its_lines = law(plane, (8, 64))
test_a_polar_plane_grows_as_its_circles = law(polar, (8, 64))
test_rounding_costs_python_nothing_more = law(rounded, (2, 64), PYTHON)
test_a_polygram_costs_python_nothing_more = law(polygram, (8, 256), PYTHON)
test_a_sphere_costs_python_nothing_more = law(sphere, (8, 32), PYTHON)
test_a_cone_costs_python_nothing_more = law(cone, (8, 32), PYTHON)
test_a_cylinder_costs_python_nothing_more = law(cylinder, (8, 32), PYTHON)
test_a_torus_costs_python_nothing_more = law(torus, (8, 32), PYTHON)
test_a_paragraph_grows_as_its_glyphs = law(paragraph, (8, 256))


def test_geometry_counts_distinguish_materialization_from_cached_reads() -> None:
    points = np.arange(21.0).reshape(7, 3)

    def read() -> None:
        mob = m.Mobject()
        mob.points = points
        np.testing.assert_array_equal(mob.points, points)
        np.testing.assert_array_equal(mob.points, points)
        assert mob._geometry.terms[0][1].key

    _, work = count(read)
    assert work.points == len(points)
    assert work.hashed == points.nbytes + len(str(points.shape).encode())


def test_a_finer_pole_search_does_not_scan_the_area() -> None:
    # its cost steps up a level at a time, so it is one pair of precisions, not a growth law
    coarse = measured(lambda: lambda: m.polylabel([U], precision=0.03))
    fine = measured(lambda: lambda: m.polylabel([U], precision=0.01))
    grown = growth(coarse, fine)
    assert max(grown.values()) <= 3 * (1 + SLACK), grown


@settings(max_examples=25)
@given(
    name=st.sampled_from(sorted(MOBJECTS)),
    copies=st.integers(2, 4),
    turn=angles(),
    scale=st.floats(0.25, 4),
    shift=st.tuples(st.floats(-3, 3), st.floats(-3, 3)),
)
def test_copies_upload_what_one_does(
    name: str, copies: int, turn: float, scale: float, shift: tuple[float, float]
) -> None:
    def show(k: int) -> Run:
        def construct(scene: m.Scene) -> None:
            group = m.Group(*(MOBJECTS[name]() for _ in range(k))).arrange(m.RIGHT)
            scene.add(group)
            scene.play(group.animate.shift([*shift, 0]).rotate(turn).scale(scale))
            scene.play(*(m.Rotate(part, turn) for part in group))

        return render(construct)

    one, many = measured(lambda: show(1)), measured(lambda: show(copies))
    assert many.uploaded == one.uploaded


@settings(max_examples=25)
@given(name=st.sampled_from(sorted(MOBJECTS)), seconds=st.integers(2, 30))
def test_holding_still_costs_the_same_however_long(name: str, seconds: int) -> None:
    # a mobject with an updater does not hold still: its updater runs every frame
    assume(not any(member.updaters for member in MOBJECTS[name]().get_family()))

    def hold(duration: float) -> Run:
        def construct(scene: m.Scene) -> None:
            scene.add(MOBJECTS[name]())
            scene.wait(duration)

        return render(construct)

    short, long = measured(lambda: hold(1)), measured(lambda: hold(seconds))
    grown = growth(short, long)
    worst = max(grown, key=lambda k: grown[k])
    assert grown[worst] <= 1 + SLACK, (
        f"held {seconds} s, {grown[worst]:.2f}x the {worst} of 1 s: {short} → {long}"
    )


def restate(mob: m.Mobject) -> None:
    """Assign each member what it holds: equal arrays, new objects."""
    for member in mob.family_members_with_points():
        member.points = member.points.copy()
        member.fill_rgbas = member.fill_rgbas.copy()
        if isinstance(member, m.MeshMobject):
            member.triangles = member.triangles.copy()
            if member.uvs is not None:
                member.uvs = member.uvs.copy()


@pytest.mark.parametrize("name", sorted(MOBJECTS))
def test_restating_what_a_mobject_holds_costs_nothing(name: str) -> None:
    """Assigning any mobject the points, colors and triangles it holds (equal arrays, new
    objects) computes, hashes and uploads nothing: all that was made of them stands."""
    mob = MOBJECTS[name]().rotate(0.3)  # (moved: its points are a placement of a shape)
    read = [member.points for member in mob.family_members_with_points()]
    assert all(points is not None for points in read)  # (read, as a frame reads them)
    _, work = count(lambda: restate(mob))
    assert (work.points, work.hashed, work.uploaded) == (0, 0, 0), work


@pytest.mark.parametrize("name", ["Square", "Text", "Sphere", "Surface", "Polygram"])
def test_restating_each_frame_costs_nothing_more(name: str) -> None:
    """A scene whose updater assigns each member what it holds, every frame, computes,
    hashes and uploads no more over 4 s than over 1 s (its Python work grows: the updater
    runs)."""

    def hold(seconds: int) -> Run:
        def construct(scene: m.Scene) -> None:
            mob = MOBJECTS[name]().rotate(0.3)
            mob.add_updater(restate)
            scene.add(mob)
            scene.wait(seconds)

        return render(construct)

    grown = growth(measured(lambda: hold(1)), measured(lambda: hold(4)))
    assert max(grown["points"], grown["hashed"], grown["uploaded"]) <= 1.1, grown


REMEMBERED = {
    "an SVG": MOBJECTS["SVGMobject"],
    "a text": lambda: m.Text("one", font="Noto Sans"),
    "another text in its font": lambda: m.Text("two", font="Noto Sans"),
    "a formula": lambda: m.MathTex("H"),
    "a Tex": lambda: m.Tex("H"),
    "a list": lambda: m.BulletedList("H"),
    "a title": lambda: m.Title("H"),
}


@pytest.mark.parametrize("name", sorted(REMEMBERED))
def test_a_remembered_construction_computes_nothing_again(name: str) -> None:
    """Made again, a construction it remembers is copied: no point computed, nothing hashed
    or uploaded (the file is read and typeset once)."""
    make = REMEMBERED[name]
    caches.clear()
    m.Text("zero", font="Noto Sans")  # (its font's capital measured)
    make()
    _, work = count(make)
    assert (work.points, work.hashed, work.uploaded) == (0, 0, 0), work


def told(story: Story, times: int) -> Run:
    """`story` told `times` times over, each telling on a fresh stage from a whole second (so
    every telling's frames fall at the same instants of it)."""

    def construct(scene: m.Scene) -> None:
        for _ in range(times):
            story.tell(scene)
            scene.clear()
            scene.wait(math.ceil(float(scene.clock) + 1e-9) - float(scene.clock))

    return render(construct)


@settings(max_examples=30)
@given(stories())
def test_a_story_costs_the_same_each_time_it_is_told(story: Story) -> None:
    try:
        told(story, 1)()
    except ValueError:  # a story may ask the impossible (see tests.scenes.outcome)
        reject()
    two, four = measured(lambda: told(story, 2)), measured(lambda: told(story, 4))
    grown = growth(two, four)
    worst = max(grown, key=lambda k: grown[k])
    target(min(grown[worst], 1e6), label="four tellings over two")
    assert grown[worst] <= 2 * (1 + SLACK), (
        f"four tellings did {grown[worst]:.2f}x the {worst} of two: {two} → {four}"
    )
