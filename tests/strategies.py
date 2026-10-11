"""Hypothesis strategies for ManimGX's values: numbers at a scene's scale, points and vectors,
Bézier curves and paths, colors and paints, rate functions, mobjects and animations.

Every strategy draws valid input only: finite numbers within a scene's reach (no NaN, infinity or
subnormal, which no scene draws), curves as their four control points, colors as ManimGX reads
them. What a test checks for invalid input it writes out by hand."""

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import numpy as np
import svgelements
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

import manimgx as m
from manimgx.animation import easing
from manimgx.drawing.paint import Paint

REACH = 100.0
"""How far from the origin a scene reaches, in scene units: twelve frames' widths."""


def reals(bound: float = REACH) -> st.SearchStrategy[float]:
    """Finite floats in [-bound, bound], 0 for any a scene cannot tell from 0 (below 1e-9)."""
    return st.floats(-bound, bound, allow_nan=False).map(
        lambda x: x if abs(x) >= 1e-9 else 0.0
    )


def arrays(
    shape: int | tuple[int, ...], bound: float = REACH
) -> st.SearchStrategy[np.ndarray]:
    """Float arrays of a shape, each entry in [-bound, bound]."""
    return hnp.arrays(np.float64, shape, elements=reals(bound))


def points(bound: float = REACH) -> st.SearchStrategy[np.ndarray]:
    """A point: (3,)."""
    return arrays(3, bound)


def vectors(
    min_norm: float = 1e-3, bound: float = 10.0
) -> st.SearchStrategy[np.ndarray]:
    """A vector no shorter than `min_norm`: a direction with a length."""
    return arrays(3, bound).filter(lambda v: np.linalg.norm(v) >= min_norm)


def angles(bound: float = 4 * np.pi) -> st.SearchStrategy[float]:
    """An angle, in radians, up to two turns either way."""
    return reals(bound)


@st.composite
def curves(
    draw: st.DrawFn, min_curves: int = 1, max_curves: int = 6, bound: float = 20.0
) -> np.ndarray:
    """The control points of a continuous path of cubic curves: (4n, 3), each curve starting
    where the one before it ends."""
    n = draw(st.integers(min_curves, max_curves))
    anchors = draw(arrays((n + 1, 3), bound))
    handles = draw(arrays((n, 2, 3), bound))
    out = np.empty((4 * n, 3))
    out[0::4], out[1::4], out[2::4], out[3::4] = (
        anchors[:-1],
        handles[:, 0],
        handles[:, 1],
        anchors[1:],
    )
    return out


@st.composite
def paths(draw: st.DrawFn, min_curves: int = 1, max_curves: int = 6) -> m.VMobject:
    """A VMobject of one subpath of cubic curves."""
    path = m.VMobject()
    path.points = draw(curves(min_curves, max_curves))
    return path


rgbs = hnp.arrays(np.float64, 3, elements=st.floats(0, 1))
rgbas = hnp.arrays(np.float64, 4, elements=st.floats(0, 1))
colors = rgbas.map(lambda x: m.ManimColor(tuple(float(c) for c in x)))


def brushes(max_rows: int = 3) -> st.SearchStrategy[np.ndarray]:
    """A brush: rows of red, green, blue and opacity (gradient stops)."""
    return hnp.arrays(
        np.float64,
        st.tuples(st.integers(1, max_rows), st.just(4)),
        elements=st.floats(0, 1),
    )


paints = st.builds(
    lambda fill, stroke, width: Paint().but(
        fill=fill, stroke=stroke, stroke_width=width
    ),
    brushes(),
    brushes(),
    st.floats(0, 16),
)

RATE_FUNCTIONS: list[Callable[[float], float]] = [
    f
    for name in easing.__all__
    if name
    not in {
        "RateFunction",
        "unit_interval",
        "zero",
        "squish_rate_func",
        "not_quite_there",
    }
    and callable(f := getattr(easing, name))
]
rate_funcs = st.sampled_from(RATE_FUNCTIONS)


# every public mobject class, made through its public constructor with small, valid arguments;
# `tests/test_tests.py` holds the registry to every class `manimgx` exports, so the laws every
# mobject keeps run over each (ArrowTip is abstract: its subclasses stand for it)
def _svg() -> m.SVGMobject:
    return m.SVGMobject(
        Path(__file__).parent / "integration/cases/svg_mobject_example/shapes.svg"
    )


def _image() -> m.ImageMobject:
    pixels = np.zeros((4, 4, 4), np.uint8)
    pixels[..., 0], pixels[..., 3] = np.arange(16).reshape(4, 4) * 16, 255
    return m.ImageMobject(pixels)


_square = lambda: m.Square()  # noqa: E731
_lines = lambda: (m.Line(m.ORIGIN, m.RIGHT), m.Line(m.ORIGIN, m.UP))  # noqa: E731
MOBJECTS: dict[str, Callable[[], m.Mobject]] = {
    "AmbientLight": lambda: m.AmbientLight(),
    "Angle": lambda: m.Angle(*_lines()),
    "AnimatedBoundary": lambda: m.AnimatedBoundary(_square()),
    "AnnotationDot": lambda: m.AnnotationDot(),
    "AnnularSector": lambda: m.AnnularSector(),
    "Annulus": lambda: m.Annulus(),
    "Arc": lambda: m.Arc(0.5, 2),
    "ArcBetweenPoints": lambda: m.ArcBetweenPoints(m.LEFT, m.RIGHT),
    "ArcBrace": lambda: m.ArcBrace(),
    "ArcPolygon": lambda: m.ArcPolygon(),
    "ArcPolygonFromArcs": lambda: m.ArcPolygonFromArcs(),
    "Arrow": lambda: m.Arrow(m.LEFT, m.RIGHT),
    "Arrow3D": lambda: m.Arrow3D(),
    "ArrowCircleFilledTip": lambda: m.ArrowCircleFilledTip(),
    "ArrowCircleTip": lambda: m.ArrowCircleTip(),
    "ArrowSquareFilledTip": lambda: m.ArrowSquareFilledTip(),
    "ArrowSquareTip": lambda: m.ArrowSquareTip(),
    "ArrowTriangleFilledTip": lambda: m.ArrowTriangleFilledTip(),
    "ArrowTriangleTip": lambda: m.ArrowTriangleTip(),
    "ArrowVectorField": lambda: m.ArrowVectorField(
        lambda p: np.array([-p[1], p[0], 0]), x_range=[-2, 2, 1], y_range=[-2, 2, 1]
    ),
    "Axes": lambda: m.Axes(),
    "BackgroundRectangle": lambda: m.BackgroundRectangle(_square()),
    "BarChart": lambda: m.BarChart([1, -2, 3]),
    "Brace": lambda: m.Brace(_square()),
    "BraceBetweenPoints": lambda: m.BraceBetweenPoints(m.LEFT, m.RIGHT),
    "BraceLabel": lambda: m.BraceLabel(_square(), "x"),
    "BraceText": lambda: m.BraceText(_square(), "side"),
    "BulletedList": lambda: m.BulletedList("one", "two"),
    "Circle": lambda: m.Circle(),
    "Code": lambda: m.Code(code_string="x = 1", language="python"),
    "ComplexPlane": lambda: m.ComplexPlane(),
    "ComplexValueTracker": lambda: m.ComplexValueTracker(1 + 2j),
    "Cone": lambda: m.Cone(),
    "ConvexHull": lambda: m.ConvexHull(*m.regular_vertices(6)[0]),
    "ConvexHull3D": lambda: m.ConvexHull3D(
        *np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]], float)
    ),
    "Cross": lambda: m.Cross(),
    "Cube": lambda: m.Cube(),
    "CubicBezier": lambda: m.CubicBezier(m.LEFT, m.UP, m.UR, m.RIGHT),
    "CurvedArrow": lambda: m.CurvedArrow(m.LEFT, m.RIGHT),
    "CurvedDoubleArrow": lambda: m.CurvedDoubleArrow(m.LEFT, m.RIGHT),
    "CurvesAsSubmobjects": lambda: m.CurvesAsSubmobjects(m.Circle()),
    "Cutout": lambda: m.Cutout(m.Square(3), m.Circle(0.5)),
    "Cylinder": lambda: m.Cylinder(),
    "DashedLine": lambda: m.DashedLine(m.LEFT, m.RIGHT),
    "DashedVMobject": lambda: m.DashedVMobject(m.Circle()),
    "DecimalMatrix": lambda: m.DecimalMatrix([[1.5, 2.25], [3.0, 4.5]]),
    "DecimalNumber": lambda: m.DecimalNumber(3.14),
    "DecimalTable": lambda: m.DecimalTable([[1.5, 2.25]]),
    "DiGraph": lambda: m.DiGraph([1, 2, 3], [(1, 2), (2, 3)], layout="circular"),
    "Difference": lambda: m.Difference(m.Square(2), m.Circle(0.5)),
    "Dodecahedron": lambda: m.Dodecahedron(),
    "Dot": lambda: m.Dot(),
    "Dot3D": lambda: m.Dot3D(),
    "DoubleArrow": lambda: m.DoubleArrow(m.LEFT, m.RIGHT),
    "Elbow": lambda: m.Elbow(),
    "Ellipse": lambda: m.Ellipse(),
    "EnvironmentLight": lambda: m.EnvironmentLight(),
    "Exclusion": lambda: m.Exclusion(m.Square(2), m.Circle(1).shift(m.RIGHT)),
    "FullScreenRectangle": lambda: m.FullScreenRectangle(),
    "FunctionGraph": lambda: m.FunctionGraph(np.sin, x_range=[-3, 3]),
    "Graph": lambda: m.Graph([1, 2, 3], [(1, 2), (2, 3)], layout="circular"),
    "Group": lambda: m.Group(m.Square(), m.Dot()),
    "Icosahedron": lambda: m.Icosahedron(),
    "ImageMobject": _image,
    "ImageMobjectFromCamera": lambda: m.ImageMobjectFromCamera(m.Camera()),
    "ImplicitFunction": lambda: m.ImplicitFunction(
        lambda x, y: x * x + y * y - 1, x_range=[-2, 2], y_range=[-2, 2]
    ),
    "Integer": lambda: m.Integer(7),
    "IntegerMatrix": lambda: m.IntegerMatrix([[1, 2], [3, 4]]),
    "IntegerTable": lambda: m.IntegerTable([[1, 2]]),
    "Intersection": lambda: m.Intersection(m.Square(2), m.Circle(1.2)),
    "Label": lambda: m.Label("x"),
    "LabeledArrow": lambda: m.LabeledArrow("a", start=m.LEFT, end=m.RIGHT),
    "LabeledDot": lambda: m.LabeledDot("1"),
    "LabeledLine": lambda: m.LabeledLine("l", start=m.LEFT, end=m.RIGHT),
    "LabeledPolygram": lambda: m.LabeledPolygram(
        [[0, 0, 0], [2, 0, 0], [1, 2, 0]], label="t"
    ),
    "Light": lambda: m.Light(m.UR),
    "Line": lambda: m.Line(m.LEFT, m.RIGHT),
    "Line3D": lambda: m.Line3D(),
    "ManimBanner": lambda: m.ManimBanner(),
    "MathTable": lambda: m.MathTable([["x", "y"]]),
    "MathTex": lambda: m.MathTex(r"e^{i\pi} + 1 = 0"),
    "MathTexPart": lambda: m.MathTex("a", "b")[0],
    "MathTypst": lambda: m.MathTypst("x^2"),
    "Matrix": lambda: m.Matrix([[1, 2], [3, 4]]),
    "MeshMobject": lambda: m.MeshMobject(),
    "Mobject": lambda: m.Mobject(),
    "Mobject1D": lambda: m.Mobject1D(),
    "MobjectMatrix": lambda: m.MobjectMatrix([[m.Dot(), m.Square(0.3)]]),
    "MobjectTable": lambda: m.MobjectTable([[m.Dot(), m.Square(0.3)]]),
    "NumberLine": lambda: m.NumberLine(),
    "NumberPlane": lambda: m.NumberPlane(),
    "Octahedron": lambda: m.Octahedron(),
    "PGroup": lambda: m.PGroup(m.PointCloudDot()),
    "PMobject": lambda: m.PMobject(),
    "Paragraph": lambda: m.Paragraph("a", "b"),
    "ParametricFunction": lambda: m.ParametricFunction(
        lambda t: np.array([np.cos(t), np.sin(2 * t), 0]), t_range=(0, 6)
    ),
    "Point": lambda: m.Point(),
    "PointCloudDot": lambda: m.PointCloudDot(),
    "PointLight": lambda: m.PointLight(),
    "PolarPlane": lambda: m.PolarPlane(),
    "Polygon": lambda: m.Polygon(m.LEFT, m.UP, m.RIGHT),
    "Polygram": lambda: m.Polygram([m.LEFT, m.UP, m.RIGHT]),
    "Polyhedron": lambda: m.Polyhedron(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]],
    ),
    "Prism": lambda: m.Prism(),
    "Rectangle": lambda: m.Rectangle(width=3, height=1),
    "RegularPolygon": lambda: m.RegularPolygon(7),
    "RegularPolygram": lambda: m.RegularPolygram(7),
    "RightAngle": lambda: m.RightAngle(*_lines()),
    "RoundedRectangle": lambda: m.RoundedRectangle(),
    "SVGMobject": _svg,
    "SampleSpace": lambda: m.SampleSpace(),
    "ScreenRectangle": lambda: m.ScreenRectangle(),
    "Sector": lambda: m.Sector(),
    "SingleStringMathTex": lambda: m.SingleStringMathTex("x^2"),
    "Sphere": lambda: m.Sphere(),
    "SpotLight": lambda: m.SpotLight(),
    "Square": lambda: m.Square(1.5),
    "Star": lambda: m.Star(),
    "StealthTip": lambda: m.StealthTip(),
    "StreamLines": lambda: m.StreamLines(
        lambda p: np.array([1.0, 0.5, 0]), x_range=[-2, 2, 1], y_range=[-2, 2, 1]
    ),
    "SunLight": lambda: m.SunLight(),
    "Surface": lambda: m.Surface(lambda u, v: np.array([u, v, u * v]), resolution=8),
    "SurroundingRectangle": lambda: m.SurroundingRectangle(m.Circle()),
    "Table": lambda: m.Table([["a", "b"]]),
    "TangentLine": lambda: m.TangentLine(m.Circle(), 0.3),
    "Tetrahedron": lambda: m.Tetrahedron(),
    "Tex": lambda: m.Tex("hello"),
    "Text": lambda: m.Text("manimgx"),
    "ThreeDAxes": lambda: m.ThreeDAxes(),
    "ThreeDVMobject": lambda: m.ThreeDVMobject(),
    "TipableVMobject": lambda: m.TipableVMobject(),
    "Title": lambda: m.Title("Title"),
    "Torus": lambda: m.Torus(),
    "TracedPath": lambda: m.TracedPath(lambda: m.ORIGIN),
    "Triangle": lambda: m.Triangle(),
    "Typst": lambda: m.Typst("*bold* text"),
    "Underline": lambda: m.Underline(m.Text("word")),
    "Union": lambda: m.Union(m.Square(2), m.Circle(1).shift(m.RIGHT)),
    "UnitInterval": lambda: m.UnitInterval(),
    "VDict": lambda: m.VDict([("s", m.Square())]),
    "VGroup": lambda: m.VGroup(m.Square(), m.Circle().shift(m.RIGHT)),
    "VMobject": lambda: m.VMobject().set_points_as_corners([m.LEFT, m.UP, m.RIGHT]),
    "VMobjectFromSVGPath": lambda: m.VMobjectFromSVGPath(
        svgelements.Path("M 0 0 L 10 10 L 20 0 Z")
    ),
    "ValueTracker": lambda: m.ValueTracker(2.5),
    "Variable": lambda: m.Variable(1.5, "x"),
    "Vector": lambda: m.Vector(m.UP),
    "VectorField": lambda: m.VectorField(lambda p: p),
    "VectorizedPoint": lambda: m.VectorizedPoint(m.UR),
}
mobjects = st.sampled_from(sorted(MOBJECTS)).map(lambda name: MOBJECTS[name]())
drawn = mobjects.filter(lambda mob: mob.boundary_box() is not None)
"""Mobjects that draw something: they have a box to lay out and measure."""


# ── animations ─────────────────────────────────────────────────────────────────────────
MONOTONE: list[Callable[[float], float]] = [
    easing.linear, easing.smooth, easing.smoothstep, easing.smootherstep,
    easing.rush_into, easing.rush_from, easing.slow_into, easing.double_smooth,
    easing.lingering, easing.exponential_decay,
    *(getattr(easing, f"ease_{way}_{kind}") for way in ("in", "out", "in_out")
      for kind in ("sine", "quad", "cubic", "quart", "quint", "expo", "circ")),
]  # fmt: skip
"""The rate functions that never go back: progress only grows with time."""

type World = list[m.Mobject]


class Played(NamedTuple):
    """An animation as the registry makes it: the mobjects it is given (`world`, made afresh
    each call), and the animation made of them (`make`)."""

    world: Callable[[], World]
    make: Callable[[World], m.Animation]


def _shape() -> World:
    return [m.Square(1.2, color=m.BLUE, fill_opacity=0.5)]


def _shapes() -> World:
    return [*_shape(), m.Circle(0.7, color=m.RED).shift(1.5 * m.RIGHT)]


def _group() -> World:
    return [m.VGroup(*_shapes())]


def _groups() -> World:
    return [m.VGroup(*_shapes()), m.VGroup(*_shapes()[::-1]).shift(m.DOWN)]


def _word() -> World:
    return [m.Text("ab")]


def _typed() -> World:
    return [m.Text("ab"), m.Rectangle(width=0.1, height=0.5)]


def _saved() -> World:
    (square,) = _shape()
    square.save_state().shift(m.RIGHT).set_color(m.YELLOW)
    return [square]


def _targeted() -> World:
    (square,) = _shape()
    square.generate_target().shift(m.RIGHT).set_color(m.YELLOW)
    return [square]


def _nothing() -> World:
    return []


def _as[T: m.Mobject](mob: m.Mobject, kind: type[T]) -> T:
    """A world's mobject, as the kind its entry made."""
    assert isinstance(mob, kind)
    return mob


class _TypeNameMatching(m.TransformMatchingAbstractBase):
    """A matching by the parts' class names (the corpus's own subclass)."""

    @staticmethod
    def get_mobject_parts(mobject: m.Mobject) -> list[m.Mobject]:
        return list(mobject.submobjects) or [mobject]

    @staticmethod
    def get_mobject_key(mobject: m.Mobject) -> str:
        return type(mobject).__name__


_SILENCE = np.zeros(4800, np.float32)  # a tenth of a second at 48 kHz

# every public animation class, made through its public constructor with small, valid arguments
# of mobjects the entry makes afresh; `tests/test_tests.py` holds the registry to every class
# `manimgx` exports, so the laws every animation keeps run over each
ANIMATIONS: dict[str, Played] = {
    "Add": Played(_shape, lambda w: m.Add(w[0])),
    "AddTextLetterByLetter": Played(_word, lambda w: m.AddTextLetterByLetter(w[0])),
    "AddTextWordByWord": Played(
        lambda: [m.Text("a b")], lambda w: m.AddTextWordByWord(w[0])
    ),
    "Animate": Played(_shape, lambda w: w[0].animate.shift(m.RIGHT).rotate(1.0)),
    "Animation": Played(_shape, lambda w: m.Animation(w[0])),
    "AnimationGroup": Played(
        _shapes,
        lambda w: m.AnimationGroup(m.FadeIn(w[0]), m.Rotate(w[1], 1.0), lag_ratio=0.3),
    ),
    "ApplyComplexFunction": Played(
        _shape, lambda w: m.ApplyComplexFunction(lambda z: z * (1 + 0.5j), w[0])
    ),
    "ApplyFunction": Played(
        _shape, lambda w: m.ApplyFunction(lambda mob: mob.shift(m.RIGHT), w[0])
    ),
    "ApplyMatrix": Played(_shape, lambda w: m.ApplyMatrix([[1, 1], [0, 1]], w[0])),
    "ApplyMethod": Played(_shape, lambda w: m.ApplyMethod(w[0].shift, m.RIGHT)),
    "ApplyPointwiseFunction": Played(
        _shape, lambda w: m.ApplyPointwiseFunction(lambda p: 1.5 * p, w[0])
    ),
    "ApplyWave": Played(_shape, lambda w: m.ApplyWave(w[0])),
    "Blink": Played(_shape, lambda w: m.Blink(w[0])),
    "Broadcast": Played(lambda: [m.Circle()], lambda w: m.Broadcast(w[0])),
    "ChangeDecimalToValue": Played(
        lambda: [m.DecimalNumber(1.0)],
        lambda w: m.ChangeDecimalToValue(_as(w[0], m.DecimalNumber), 3.0),
    ),
    "ChangeSpeed": Played(
        _shape, lambda w: m.ChangeSpeed(m.Rotate(w[0], 1.0), {0.5: 2})
    ),
    "ChangingDecimal": Played(
        lambda: [m.DecimalNumber(1.0)],
        lambda w: m.ChangingDecimal(_as(w[0], m.DecimalNumber), lambda a: 1 + 2 * a),
    ),
    "Circumscribe": Played(_shape, lambda w: m.Circumscribe(w[0])),
    "ClockwiseTransform": Played(_shapes, lambda w: m.ClockwiseTransform(w[0], w[1])),
    "ComplexHomotopy": Played(
        _shape, lambda w: m.ComplexHomotopy(lambda z, t: z * (1 + t), w[0])
    ),
    "CounterclockwiseTransform": Played(
        _shapes, lambda w: m.CounterclockwiseTransform(w[0], w[1])
    ),
    "Create": Played(_shape, lambda w: m.Create(w[0])),
    "CyclicReplace": Played(_shapes, lambda w: m.CyclicReplace(w[0], w[1])),
    "DrawBorderThenFill": Played(_shape, lambda w: m.DrawBorderThenFill(w[0])),
    "FadeIn": Played(_shape, lambda w: m.FadeIn(w[0], shift=m.UP)),
    "FadeOut": Played(_shape, lambda w: m.FadeOut(w[0], scale=0.5)),
    "FadeToColor": Played(_shape, lambda w: m.FadeToColor(w[0], m.YELLOW)),
    "FadeTransform": Played(_shapes, lambda w: m.FadeTransform(w[0], w[1])),
    "FadeTransformPieces": Played(_groups, lambda w: m.FadeTransformPieces(w[0], w[1])),
    "Flash": Played(_nothing, lambda w: m.Flash(m.ORIGIN)),
    "FocusOn": Played(_nothing, lambda w: m.FocusOn(m.ORIGIN)),
    "GrowArrow": Played(
        lambda: [m.Arrow(m.LEFT, m.RIGHT)], lambda w: m.GrowArrow(w[0])
    ),
    "GrowFromCenter": Played(_shape, lambda w: m.GrowFromCenter(w[0])),
    "GrowFromEdge": Played(_shape, lambda w: m.GrowFromEdge(w[0], m.UP)),
    "GrowFromPoint": Played(_shape, lambda w: m.GrowFromPoint(w[0], m.LEFT)),
    "Homotopy": Played(
        _shape, lambda w: m.Homotopy(lambda x, y, z, t: (x + t, y, z), w[0])
    ),
    "Indicate": Played(_shape, lambda w: m.Indicate(w[0])),
    "LaggedStart": Played(
        _shapes,
        lambda w: m.LaggedStart(m.FadeIn(w[0]), m.Rotate(w[1], 1.0), lag_ratio=0.5),
    ),
    "LaggedStartMap": Played(_group, lambda w: m.LaggedStartMap(m.FadeIn, w[0])),
    "MaintainPositionRelativeTo": Played(
        _shapes, lambda w: m.MaintainPositionRelativeTo(w[0], w[1])
    ),
    "MoveAlongPath": Played(
        lambda: [m.Dot(), m.Line(m.LEFT, m.RIGHT)],
        lambda w: m.MoveAlongPath(w[0], _as(w[1], m.VMobject)),
    ),
    "MoveToTarget": Played(_targeted, lambda w: m.MoveToTarget(w[0])),
    "PhaseFlow": Played(
        _shape, lambda w: m.PhaseFlow(lambda p: np.array([-p[1], p[0], 0.0]), w[0])
    ),
    "RemoveTextLetterByLetter": Played(
        _word, lambda w: m.RemoveTextLetterByLetter(w[0])
    ),
    "ReplacementTransform": Played(
        _shapes, lambda w: m.ReplacementTransform(w[0], w[1])
    ),
    "Restore": Played(_saved, lambda w: m.Restore(w[0])),
    "Rotate": Played(_shape, lambda w: m.Rotate(w[0], 1.0)),
    "Rotating": Played(_shape, lambda w: m.Rotating(w[0])),
    "ScaleInPlace": Played(_shape, lambda w: m.ScaleInPlace(w[0], 2.0)),
    "ShowIncreasingSubsets": Played(_group, lambda w: m.ShowIncreasingSubsets(w[0])),
    "ShowPassingFlash": Played(_shape, lambda w: m.ShowPassingFlash(w[0])),
    "ShowPassingFlashWithThinningStrokeWidth": Played(
        _shape, lambda w: m.ShowPassingFlashWithThinningStrokeWidth(w[0])
    ),
    "ShowSubmobjectsOneByOne": Played(
        _group, lambda w: m.ShowSubmobjectsOneByOne(w[0])
    ),
    "ShrinkToCenter": Played(_shape, lambda w: m.ShrinkToCenter(w[0])),
    "Sound": Played(_nothing, lambda w: m.Sound(_SILENCE, rate=48000)),
    "Speech": Played(_nothing, lambda w: m.Speech(_SILENCE, text="a", rate=48000)),
    "SpinInFromNothing": Played(_shape, lambda w: m.SpinInFromNothing(w[0])),
    "SpiralIn": Played(_group, lambda w: m.SpiralIn(w[0])),
    "Succession": Played(
        _shapes, lambda w: m.Succession(m.FadeIn(w[0]), m.Rotate(w[1], 1.0))
    ),
    "Swap": Played(_shapes, lambda w: m.Swap(w[0], w[1])),
    "Transform": Played(_shapes, lambda w: m.Transform(w[0], w[1])),
    "TransformFromCopy": Played(_shapes, lambda w: m.TransformFromCopy(w[0], w[1])),
    "TransformMatchingAbstractBase": Played(
        _groups, lambda w: _TypeNameMatching(w[0], w[1], fade_transform_mismatches=True)
    ),
    "TransformMatchingShapes": Played(
        _groups, lambda w: m.TransformMatchingShapes(w[0], w[1])
    ),
    "TransformMatchingTex": Played(
        lambda: [m.MathTex("a", "b"), m.MathTex("b", "a")],
        lambda w: m.TransformMatchingTex(w[0], w[1]),
    ),
    "TypeWithCursor": Played(_typed, lambda w: m.TypeWithCursor(w[0], w[1])),
    "Uncreate": Played(_shape, lambda w: m.Uncreate(w[0])),
    "UntypeWithCursor": Played(_typed, lambda w: m.UntypeWithCursor(w[0], w[1])),
    "Unwrite": Played(_shape, lambda w: m.Unwrite(w[0])),
    "UpdateFromAlphaFunc": Played(
        _shape, lambda w: m.UpdateFromAlphaFunc(w[0], lambda mob, a: mob.set_x(a))
    ),
    "UpdateFromFunc": Played(
        _shape, lambda w: m.UpdateFromFunc(w[0], lambda mob: mob.set_y(1.0))
    ),
    "Wait": Played(_nothing, lambda w: m.Wait()),
    "Wiggle": Played(_group, lambda w: m.Wiggle(w[0])),
    "Write": Played(_word, lambda w: m.Write(w[0])),
}
