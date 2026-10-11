# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Ported from Manim CE 0.21 (MIT)."""

from __future__ import annotations

import functools
import warnings
from warnings import deprecated

__all__ = [
    "Arrow3D",
    "Cone",
    "ConvexHull3D",
    "Cube",
    "Cylinder",
    "Dodecahedron",
    "Dot3D",
    "Icosahedron",
    "Line3D",
    "Octahedron",
    "Polyhedron",
    "Prism",
    "Sphere",
    "Surface",
    "Tetrahedron",
    "ThreeDVMobject",
    "Torus",
]
from collections.abc import Callable, Hashable, Iterable, Sequence
from typing import TYPE_CHECKING, ClassVar, Literal, Self, Unpack, cast

import numpy as np
from typing_extensions import TypedDict

from manimgx.caches import forgets
from manimgx.constants import (
    DEFAULT_DOT_RADIUS,
    DOWN,
    IN,
    LEFT,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    TAU,
    UP,
    Y_AXIS,
    Z_AXIS,
    LineJointType,
)
from manimgx.drawing.geometry import (
    Lattice,
    QuickHull,
    normalize,
    perpendicular_bisector,
    rotation_about_z,
    rotation_matrix,
    sample,
    z_to_vector,
)
from manimgx.drawing.paint import (
    BLUE,
    BLUE_D,
    BLUE_E,
    LIGHT_GREY,
    WHITE,
    Colorscale,
    ManimColor,
    ParsableManimColor,
    Style,
    _Style,
    rgbas_by_value,
)
from manimgx.mobject import MeshMobject, Mobject, VectorizedPoint, VGroup, VMobject
from manimgx.mobjects.graph import Graph, GraphOptions
from manimgx.mobjects.shapes import Circle, Polygon, Square

if TYPE_CHECKING:
    from manimgx.mobjects.plotting import ThreeDAxes
    from manimgx.typing import (
        Point3D,
        Point3DLike,
        Point3DLike_Array,
        Vector3D,
        Vector3DLike,
    )


@deprecated(
    "ThreeDVMobject(...) is VMobject(..., shade_in_3d=True): use it", category=None
)
class ThreeDVMobject(VMobject):
    """A path shaded by a three-dimensional scene's light: a
    [VMobject][manimgx.VMobject] with `shade_in_3d` on.

    It takes a VMobject's arguments. Give it points in three dimensions (with
    `set_points_as_corners`, `set_points_smoothly`, …) to draw a curve through space
    that the light shades as it does the other three-dimensional objects.
    """

    # u_index … v2: a surface face's place in its (u, v) grid; nothing sets them (a
    # Surface is one mesh, not faces of this class)
    defaults: ClassVar[Style] = {"shade_in_3d": True}
    u_index: int
    v_index: int
    u1: float
    u2: float
    v1: float
    v2: float


class _SurfaceLook(_Style, total=False):
    """SurfaceLook's keys, open, for the keywords that add to them."""

    surface_piece_config: Style | None
    """Accepted for Manim compatibility; ignored."""
    checkerboard_colors: Iterable[ParsableManimColor] | Literal[False]
    """The colors the faces are checkered with, in turn along both u and v (default
    `BLUE_D` and `BLUE_E`, a cone's False; False: the fill color alone)."""
    should_make_jagged: bool
    """Accepted for Manim compatibility; ignored."""
    pre_function_handle_to_anchor_scale_factor: float
    """Accepted for Manim compatibility; ignored."""


class SurfaceLook(_SurfaceLook, total=False, closed=True):
    """A [Surface][manimgx.Surface]'s keywords but its function, ranges and resolution,
    for the shapes that set those (spheres, cylinders, …): its checkerboard, with the
    style keywords."""


class SurfaceOptions(_SurfaceLook, total=False, closed=True):
    """A [Surface][manimgx.Surface]'s keywords but its function and ranges, for the
    shapes that pass them on ([Cone][manimgx.Cone]): its resolution and checkerboard,
    with the style keywords."""

    resolution: int | Sequence[int]
    """How many faces the surface has along u and along v: one positive integer for
    both, or a pair of positive integers `(u, v)` (default 32)."""


_COLORMAP_TEXELS = 256  # a colorscale's samples along the value, as a texture


@forgets
@functools.cache
def _checkerboard(
    palette: tuple[tuple[float, float, float, float], ...],
    u_count: int,
    v_count: int,
    opacity: float,
) -> np.ndarray:
    """A checkerboard's rows — one color per cell: a value of its palette,
    grid and opacity."""
    k = np.arange(u_count * v_count)
    rows = np.array(palette)[(k // v_count + k % v_count) % len(palette)]
    rows[:, 3] = opacity
    rows.flags.writeable = False
    return rows


class Surface(MeshMobject):
    """A parametric surface: the points `func(u, v)` for u and v over their ranges,
    drawn as the smooth surface through them; checkered in two blues, with thin light
    grey edges, and shaded by a three-dimensional scene's light, unless styled.

    The ranges are divided into `resolution` steps, along u and along v, and the
    function is sampled at the corners of the grid's cells, the surface's faces. What is
    drawn is the smooth surface through those samples, not flat faces: `resolution` sets
    how closely it follows the function, and the light shades it smoothly, across the
    seam too where the surface closes on itself (a sphere, a torus, a cylinder). Each
    face keeps its own colors, so a checkerboard keeps sharp cells, and the stroke draws
    the faces' edges, curved with the surface. The faces are one mesh (a
    [MeshMobject][manimgx.MeshMobject]): it morphs into other meshes (drawn as flat
    faces while it morphs into one of another grid), and [Create][manimgx.Create] draws
    it in face by face, each face with its edges.
    [set_fill_by_checkerboard][manimgx.Surface.set_fill_by_checkerboard] and
    [set_fill_by_value][manimgx.Surface.set_fill_by_value] color it.

    The checkerboard palette supplies the initial paint; use
    [set_fill_by_checkerboard][manimgx.Surface.set_fill_by_checkerboard] to recolor
    the surface later. The initial palette and ignored compatibility options are
    not retained as instance attributes.

    Args:
        func: The function, from (u, v) to a point in scene coordinates (on axes, their
            [c2p][manimgx.Axes.coords_to_point] of coordinates).
        u_range: The range of u, `(u_min, u_max)`.
        v_range: The range of v, `(v_min, v_max)`.
        resolution: How many faces the surface has along u and along v: one positive
            integer for both, or a pair of positive integers `(u, v)`.
        surface_piece_config: Accepted for Manim compatibility; ignored.
        checkerboard_colors: The initial checkerboard colors, in turn; False for the
            fill color alone.
        should_make_jagged: Accepted for Manim compatibility; ignored.
        pre_function_handle_to_anchor_scale_factor: Accepted for Manim compatibility;
            ignored.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class SurfaceExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=60 * m.DEGREES, theta=-60 * m.DEGREES)

                def mobius(u: float, v: float) -> np.ndarray:
                    r = 2.5 + v * np.cos(u / 2)
                    return np.array([r * np.cos(u), r * np.sin(u), v * np.sin(u / 2)])

                strip = m.Surface(
                    mobius, u_range=(0, m.TAU), v_range=(-1, 1), resolution=(48, 6)
                )
                self.add(strip)
        ```
    """

    # one mesh, func(u, v) sampled over a grid of faces, drawn as the C² cubic spline
    # through its samples (see `feed.refine_surface`: periodic along a direction whose
    # ends meet, not-a-knot otherwise). Paint belongs to lattice cells; the renderer
    # derives their independently colored blocks and edge loops. Unequal lattices
    # align as explicit triangle soup.
    defaults: ClassVar[Style] = {
        "fill_color": BLUE_D,
        "fill_opacity": 1.0,
        "stroke_color": LIGHT_GREY,
        "stroke_width": 0.5,
        "stroke_opacity": 1.0,
        "shade_in_3d": True,
    }

    def __init__(
        self,
        func: Callable[[float, float], np.ndarray],
        u_range: Sequence[float] = (0, 1),
        v_range: Sequence[float] = (0, 1),
        resolution: int | Sequence[int] = 32,
        surface_piece_config: Style | None = None,
        checkerboard_colors: Iterable[ParsableManimColor] | Literal[False] = (
            BLUE_D,
            BLUE_E,
        ),
        should_make_jagged: bool = False,
        pre_function_handle_to_anchor_scale_factor: float = 1e-05,
        **kwargs: Unpack[Style],
    ) -> None:
        self.u_range = list(u_range)  # values, as they are given
        self.v_range = list(v_range)
        self.resolution = resolution
        colors: list[ManimColor] | Literal[False] = (
            False
            if checkerboard_colors is False
            else [ManimColor(c) for c in checkerboard_colors]
        )
        self._func = func
        super().__init__(**kwargs)
        if colors:
            self.set_fill_by_checkerboard(*colors)

    def func(self, u: float, v: float) -> np.ndarray:
        """The surface's point at (u, v): its function's value.

        Args:
            u: The first parameter.
            v: The second parameter.

        Returns:
            The point, in scene coordinates, as the surface was made (before it was
            moved).
        """
        return self._func(u, v)

    def generate_points(self) -> Self:
        u_res, v_res = (
            (self.resolution, self.resolution)
            if isinstance(self.resolution, int)
            else self.resolution
        )
        if u_res <= 0 or v_res <= 0:
            raise ValueError("Surface resolution must be positive in both directions")
        u = np.linspace(self.u_range[0], self.u_range[1], u_res + 1)
        v = np.linspace(self.v_range[0], self.v_range[1], v_res + 1)
        grid = sample(self.func, *np.meshgrid(u, v, indexing="ij"))
        self.points = grid.reshape(-1, 3)
        self._topology = Lattice.of(len(u) - 1, len(v) - 1)
        self.uvs = None
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def face_indices(self) -> tuple[np.ndarray, np.ndarray]:
        """The place of every face in the surface's grid: its index along u and its
        index along v, in the mesh's order.

        Returns:
            Two arrays, the faces' indices along u and along v.
        """
        grid = self.grid
        if grid is None:
            raise ValueError("Checkerboard cells require lattice topology")
        u, v = grid
        k = np.arange(u * v)
        return k // v, k % v

    def _paint_faces(self, colors: np.ndarray, opacity: float | None) -> Self:
        """One color per cell — (cells, 4) RGBA; opacity as given, else
        as it was."""
        rows = colors.copy()
        rows[:, 3] = self._opacity(opacity, len(rows))
        return self._fill_rows(rows)

    def _fill_rows(self, rows: np.ndarray) -> Self:
        """Colors as the surface's fill, in place of a colormap."""
        self.paint = self.paint.but(fill=rows, texture=None, colormap=False)
        return self

    def _opacity(self, opacity: float | None, count: int) -> float | np.ndarray:
        """The opacity faces are painted with: as given, else as it was (per cell, or one)."""
        current = self.paint.fill
        if opacity is not None:
            return opacity
        return current[:, 3] if len(current) == count else float(current[0, 3])

    def set_fill_by_checkerboard(
        self, *colors: ParsableManimColor, opacity: float | None = None
    ) -> Self:
        """Color the faces like a checkerboard: the colors in turn, along u and along v.

        The face at place (i, j) of the grid takes the color i + j places along
        `colors`, cycling: two colors make a checkerboard, more make diagonal stripes.
        It replaces the colors [set_fill_by_value][manimgx.Surface.set_fill_by_value]
        gave.

        Args:
            *colors: The colors, in turn.
            opacity: The faces' opacity, from 0 to 1; None to keep theirs.
        """
        palette = tuple(tuple(ManimColor(c).to_rgba()) for c in colors)
        grid = self.grid
        if grid is None:
            raise ValueError("Checkerboard cells require lattice topology")
        alpha = self._opacity(opacity, grid[0] * grid[1])
        # one opacity: the checkerboard is a value, made once
        if isinstance(alpha, float):
            return self._fill_rows(_checkerboard(palette, *grid, alpha))
        i, j = self.face_indices()
        return self._paint_faces(np.array(palette)[(i + j) % len(palette)], opacity)

    def set_fill_by_value(
        self,
        axes: ThreeDAxes,
        colorscale: Colorscale | None = None,
        axis: int = 2,
        colors: Colorscale | None = None,
    ) -> Self:
        """Color the surface point by point by a coordinate on axes: its height, z, by
        default, on a colorscale.

        Each sample of the surface has its coordinate along `axis`, and the values are
        blended across the surface before the colorscale maps them: the colors follow
        the surface smoothly, and a face whose corners straddle a color of the scale
        shows it. The colors are the fill's, lit as a fill color is, at the fill's
        opacity: a fill color set later ([set_fill][manimgx.Mobject.set_fill],
        [set_color][manimgx.Mobject.set_color]) replaces them, as
        [set_fill_by_checkerboard][manimgx.Surface.set_fill_by_checkerboard] does.
        Without a colorscale, it warns and leaves the colors as they are.

        Args:
            axes: The axes whose coordinates color the surface.
            colorscale: The colors: spread evenly over the axes' range along `axis`, or
                `(color, value)` pairs, which span their own values; blended between,
                and held beyond the ends.
            axis: The coordinate: 0 for x, 1 for y, 2 for z.
            colors: The colorscale by its older name, accepted for Manim compatibility:
                used when `colorscale` is None.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class SurfaceSetFillByValueExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=65 * m.DEGREES, theta=-130 * m.DEGREES
                    )
                    axes = m.ThreeDAxes(
                        x_range=(0, 5),
                        y_range=(0, 5),
                        z_range=(-1, 1, 0.5),
                        x_length=7,
                        y_length=7,
                        z_length=3,
                    )
                    surface = m.Surface(
                        lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
                        u_range=(0, 5),
                        v_range=(0, 5),
                        resolution=8,
                    )
                    surface.set_fill_by_value(
                        axes, colorscale=[(m.RED, -0.5), (m.YELLOW, 0), (m.GREEN, 0.5)]
                    )
                    self.add(axes, surface)
            ```
        """
        # the colorscale is a texture along the value (a colormap) and each sample's
        # value its coordinate: values are interpolated over the surface before they are
        # mapped
        colorscale = colorscale if colorscale is not None else colors
        if colorscale is None:
            warnings.warn(
                "The value passed to the colorscale keyword argument was None, the"
                " surface fill color has not been changed",
                stacklevel=2,
            )
            return self
        low, high = (axes.x_range, axes.y_range, axes.z_range or (0, 0))[axis][:2]
        if all(isinstance(c, (tuple, list)) and len(c) == 2 for c in colorscale):
            pivots = [
                float(cast("tuple[ParsableManimColor, float]", c)[1])
                for c in colorscale
            ]
            low, high = min(pivots), max(pivots)
        values = np.asarray(axes.point_to_coords(self.points), dtype=float)[:, axis]
        span = high - low if high > low else 1.0
        n = _COLORMAP_TEXELS
        ramp = rgbas_by_value(colorscale, np.linspace(low, high, n), low, high)
        colormap = (ramp[None] * 255).round().astype(np.uint8)
        colormap[..., 3] = 255
        colormap.flags.writeable = False
        # texel centers: the ends hold beyond them
        u = (0.5 + np.clip((values - low) / span, 0.0, 1.0) * (n - 1)) / n
        self.uvs = np.stack([u, np.full_like(u, 0.5)], axis=1)
        grid = self.grid
        count = len(self.points) if grid is None else grid[0] * grid[1]
        alpha = self._opacity(None, count)
        fill = np.ones((1 if isinstance(alpha, float) else count, 4))
        fill[:, 3] = alpha
        self.paint = self.paint.but(fill=fill, texture=colormap, colormap=True)
        return self


def _revolve(
    radius: float | np.ndarray,
    height: float | np.ndarray,
    angle: float | np.ndarray,
) -> np.ndarray:
    """Turn a radial profile about z, at one angle or a grid of angles."""
    return np.array([radius * np.cos(angle), radius * np.sin(angle), height])


class Sphere(Surface):
    """A sphere: checkered in two blues and shaded by a three-dimensional scene's light,
    unless styled.

    It is a [Surface][manimgx.Surface] of u, the longitude, and v, the angle from the
    south pole (the bottom, along z): their ranges may cut out a part of it.

    Args:
        center: Where its center goes.
        radius: Its radius, in scene units.
        resolution: How many faces it has around and from pole to pole: one number for
            both, or `(u, v)`; None for (24, 12).
        u_range: The range of the longitude, in radians: (0, τ) goes all the way
            around.
        v_range: The range of the angle from the south pole, in radians: (0, π) goes
            from pole to pole.
        **kwargs: [Surface keywords][manimgx.mobjects.three_d.SurfaceLook]:
            `checkerboard_colors`, and the style keywords.

    Examples:
        ```python
        import manimgx as m


        class SphereExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-90 * m.DEGREES)
                self.add(
                    m.Sphere(center=(-4, 0, 0), radius=1.5),
                    m.Sphere(radius=1.5, resolution=(12, 6)).set_color(m.GREEN),
                    m.Sphere(
                        center=(4, 0, 0),
                        radius=1.5,
                        v_range=(0, m.PI / 2),
                        checkerboard_colors=[m.RED, m.YELLOW],
                    ),
                )
        ```
    """

    def __init__(
        self,
        center: Point3DLike = ORIGIN,
        radius: float = 1,
        resolution: int | Sequence[int] | None = None,
        u_range: Sequence[float] = (0, TAU),
        v_range: Sequence[float] = (0, PI),
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        self.radius = radius
        super().__init__(
            self.func,
            resolution=resolution if resolution is not None else (24, 12),
            u_range=u_range,
            v_range=v_range,
            **kwargs,
        )
        self.shift(center)

    def func(self, u: float, v: float) -> Point3D:
        """The sphere's point at a longitude and an angle from its south pole, as it is
        made around the origin.

        Args:
            u: The longitude, in radians, counterclockwise from the x-axis.
            v: The angle from the south pole, in radians: 0 at the bottom, π at the
                top.

        Returns:
            The point, relative to the sphere's center.
        """
        return self.radius * _revolve(np.sin(v), -np.cos(v), u)


class Dot3D(Sphere):
    """A dot in three dimensions: a small sphere, white unless given a color.

    Args:
        point: Where its center goes.
        radius: Its radius, in scene units.
        resolution: How many faces it has around and from pole to pole: one number for
            both, or `(u, v)`; None for (24, 12).
        **kwargs: [Surface keywords][manimgx.mobjects.three_d.SurfaceLook]:
            `color` paints it all in one color; the style keywords.

    Examples:
        ```python
        import manimgx as m


        class Dot3DExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
                axes = m.ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-2, 2))
                self.add(
                    axes,
                    m.Dot3D(axes.c2p(0, 0, 1.5), radius=0.2, color=m.RED),
                    m.Dot3D(axes.c2p(2, 0, 0), radius=0.2, color=m.BLUE),
                    m.Dot3D(axes.c2p(0, 2, 0), radius=0.2, color=m.YELLOW),
                )
        ```
    """

    def __init__(
        self,
        point: Point3DLike = ORIGIN,
        radius: float = DEFAULT_DOT_RADIUS,
        resolution: int | tuple[int, int] | None = (8, 8),
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        color = kwargs.pop("color", None) or WHITE  # one color, over the checkerboard
        super().__init__(center=point, radius=radius, resolution=resolution, **kwargs)
        self.set_color(color)


class Cube(VGroup):
    """A cube: six square faces, centered at the origin with its edges along the axes;
    blue, three-quarters opaque, without edges and shaded by a three-dimensional
    scene's light, unless styled.

    Args:
        side_length: The length of its edges, in scene units.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] for its faces.

    Examples:
        ```python
        import manimgx as m


        class CubeExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
                cubes = m.Group(
                    m.Cube(),
                    m.Cube(side_length=3, fill_color=m.TEAL, fill_opacity=1),
                    m.Cube(fill_opacity=0.3, stroke_width=2, stroke_color=m.YELLOW),
                ).arrange(buff=1.5)
                self.add(cubes)
        ```
    """

    defaults: ClassVar[Style] = {
        "fill_opacity": 0.75,
        "fill_color": BLUE,
        "stroke_width": 0,
    }

    def __init__(self, side_length: float = 2, **kwargs: Unpack[Style]) -> None:
        self.side_length = side_length
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        for vect in (IN, OUT, LEFT, RIGHT, UP, DOWN):
            face = Square(
                side_length=self.side_length,
                shade_in_3d=True,
                joint_type=LineJointType.BEVEL,
            )
            face.flip()
            face.shift(self.side_length * OUT / 2.0)
            face.apply_matrix(z_to_vector(vect))
            self.add(face)
        return self


class Prism(Cube):
    """A box: a [Cube][manimgx.Cube] stretched to its width, height and depth; blue,
    three-quarters opaque, without edges and shaded by a three-dimensional scene's
    light, unless styled.

    Args:
        dimensions: Its size along x, y and z, in scene units; None for (3, 2, 1).
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] for its faces.

    Examples:
        ```python
        import manimgx as m


        class PrismExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=60 * m.DEGREES, theta=-60 * m.DEGREES)
                prisms = m.Group(
                    m.Prism(),
                    m.Prism(dimensions=[1, 2, 3], fill_color=m.GREEN),
                ).arrange(buff=1.5)
                self.add(prisms)
        ```
    """

    def __init__(
        self, dimensions: Vector3DLike | None = None, **kwargs: Unpack[Style]
    ) -> None:
        self.dimensions = (
            [3.0, 2.0, 1.0] if dimensions is None else [float(d) for d in dimensions]
        )
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        super().generate_points()
        for dim, value in enumerate(self.dimensions):
            self.rescale_to_fit(value, dim, stretch=True)
        return self


class _DirectedSurface(Surface):
    direction: Vector3D
    _current_theta: float
    _current_phi: float

    def set_direction(self, direction: Vector3DLike) -> Self:
        """Turn the surface's axis to a direction, undoing its previous direction.

        Both turns are about the origin, preserving other changes to the surface.

        Args:
            direction: The direction of the axis, from a cone's base to its apex.
        """
        self.direction = np.array(direction, dtype=float)
        x, y, z = self.direction
        r = np.sqrt(x**2 + y**2 + z**2)
        theta = float(np.arccos(z / r)) if r > 0 else 0.0
        if x == 0:
            phi = 0.0 if y == 0 else float(np.arctan(np.inf)) + (PI if y < 0 else 0)
        else:
            phi = float(np.arctan(y / x))
        if x < 0:
            phi += PI
        turn = (
            rotation_about_z(phi)
            @ rotation_matrix(theta - self._current_theta, Y_AXIS)
            @ rotation_about_z(-self._current_phi)
        )
        self._rotate_direction_state(turn)
        self._apply_linear(turn, ORIGIN)
        self._current_theta, self._current_phi = theta, phi
        return self


class Cone(_DirectedSurface):
    """A cone, its apex at the origin, pointing along `direction` from its base; blue,
    shaded by a three-dimensional scene's light, and open at the base, unless styled.

    It is a [Surface][manimgx.Surface] of u, the distance from the apex along its side,
    and v, the angle around its axis: `v_range` may cut out a slice, and `u_min` its
    tip. It is one color, not checkered, unless given `checkerboard_colors`.

    Args:
        base_radius: The radius of its base, in scene units.
        height: Its height, from its base to its apex, in scene units.
        direction: The direction it points in, from its base to its apex.
        show_base: Whether a disc closes its base.
        v_range: The range of the angle around its axis, in radians: (0, τ) goes all
            the way around.
        u_min: Where its side begins, as a distance from the apex along it, in scene
            units: above 0, the tip is cut off.
        **kwargs: [Surface keywords][manimgx.mobjects.three_d.SurfaceOptions]:
            `resolution`, `checkerboard_colors`, and the style keywords.

    Examples:
        ```python
        import manimgx as m


        class ConeExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-60 * m.DEGREES)
                frustum = m.Cone(base_radius=1.5, height=3, u_min=1.5, fill_color=m.RED)
                self.add(
                    m.Cone(base_radius=1.5, height=3).shift(4 * m.LEFT + 1.5 * m.OUT),
                    m.Cone(direction=m.X_AXIS + m.Z_AXIS, show_base=True),
                    frustum.shift(4 * m.RIGHT + 1.5 * m.OUT),
                )
        ```
    """

    def __init__(
        self,
        base_radius: float = 1,
        height: float = 1,
        direction: Vector3DLike = Z_AXIS,
        show_base: bool = False,
        v_range: Sequence[float] = (0, TAU),
        u_min: float = 0,
        **kwargs: Unpack[SurfaceOptions],
    ) -> None:
        self.direction = np.array(direction, dtype=float)
        self.theta = PI - np.arctan(base_radius / height)
        kwargs.setdefault("checkerboard_colors", False)
        super().__init__(
            self.func,
            v_range=v_range,
            u_range=(u_min, np.sqrt(base_radius**2 + height**2)),
            **kwargs,
        )
        self.new_height = height
        self._current_theta = 0.0
        self._current_phi = 0.0
        self.base_circle = Circle(
            radius=base_radius,
            color=self.fill_color,
            fill_opacity=self.fill_opacity,
            stroke_width=0,
        )
        """The disc of its base, in its fill color: part of the cone with
        `show_base`."""
        self.base_circle.shift(height * IN)
        self._set_start_and_end_attributes(self.direction)
        if show_base:
            self.add(self.base_circle)
        self.set_direction(direction)

    def func(self, u: float, v: float) -> Point3D:
        """The cone's point, as it is made pointing up (along z) with its apex at the
        origin, at a distance from the apex along its side and an angle around its axis.

        Args:
            u: The distance from the apex, along the side, in scene units.
            v: The angle around the axis, in radians.

        Returns:
            The point, in scene coordinates.
        """
        return _revolve(u * np.sin(self.theta), u * np.cos(self.theta), v)

    def _set_start_and_end_attributes(self, direction: Vector3D) -> None:
        normalized_direction = direction * np.linalg.norm(direction)
        start = self.base_circle.get_center()
        end = start + normalized_direction * self.new_height
        self.start_point = VectorizedPoint(start)
        self.end_point = VectorizedPoint(end)
        self.add(self.start_point, self.end_point)


class Cylinder(_DirectedSurface):
    """A cylinder, centered at the origin, its axis along `direction`: checkered in two
    blues, closed at both ends by discs, and shaded by a three-dimensional scene's
    light, unless styled.

    It is a [Surface][manimgx.Surface] of u, the height along its axis, and v, the
    angle around it: `v_range` may cut out a slice.

    Args:
        radius: Its radius, in scene units.
        height: Its height, along its axis, in scene units.
        direction: The direction of its axis.
        v_range: The range of the angle around its axis, in radians: (0, τ) goes all
            the way around.
        show_ends: Whether discs close its ends.
        resolution: How many faces it has along its axis and around it: one number for
            both, or `(u, v)`.
        **kwargs: [Surface keywords][manimgx.mobjects.three_d.SurfaceLook]:
            `checkerboard_colors`, and the style keywords.

    Examples:
        ```python
        import manimgx as m


        class CylinderExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-60 * m.DEGREES)
                self.add(
                    m.Cylinder(radius=1.5, height=3).shift(4.5 * m.LEFT),
                    m.Cylinder(radius=0.5, height=4, direction=m.X_AXIS + m.Z_AXIS),
                    m.Cylinder(show_ends=False, v_range=(0, m.PI)).shift(4 * m.RIGHT),
                )
        ```
    """

    def __init__(
        self,
        radius: float = 1,
        height: float = 2,
        direction: Vector3DLike = Z_AXIS,
        v_range: Sequence[float] = (0, TAU),
        show_ends: bool = True,
        resolution: int | Sequence[int] = (24, 24),
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        self._height = height
        self.radius = radius
        super().__init__(
            self.func,
            resolution=resolution,
            u_range=(-self._height / 2, self._height / 2),
            v_range=v_range,
            **kwargs,
        )
        if show_ends:
            self.add_bases()
        self._current_phi = 0.0
        self._current_theta = 0.0
        self.set_direction(direction)

    def func(self, u: float, v: float) -> np.ndarray:
        """The cylinder's point, as it is made along z and centered on the origin, at a
        height along its axis and an angle around it.

        Args:
            u: The height along the axis, in scene units, from the middle.
            v: The angle around the axis, in radians.

        Returns:
            The point, in scene coordinates.
        """
        return _revolve(self.radius, u, v)

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def add_bases(self) -> Self:
        """Add the discs that close the cylinder's ends: `base_top` and `base_bottom`,
        in its fill color.

        They are placed at the ends of a cylinder along z, centered on the origin, as
        it is made: the constructor adds them (with `show_ends`) before turning the
        cylinder to its direction.
        """
        bases = [
            Circle(
                radius=self.radius,
                color=self.fill_color,
                fill_opacity=self.fill_opacity,
                shade_in_3d=True,
                stroke_width=0,
            )
            for _ in range(2)
        ]
        self.base_top, self.base_bottom = bases
        self.base_top.shift(self.u_range[1] * IN)
        self.base_bottom.shift(self.u_range[0] * IN)
        self.add(self.base_top, self.base_bottom)
        return self


class Line3DOptions(_SurfaceLook, total=False, closed=True):
    """A [Line3D][manimgx.Line3D]'s keywords but its ends, for the methods that pass
    them on ([parallel_to][manimgx.Line3D.parallel_to],
    [perpendicular_to][manimgx.Line3D.perpendicular_to]): its thickness and resolution,
    with the surface keywords."""

    thickness: float
    """The line's radius, in scene units (default 0.02)."""
    resolution: int | tuple[int, int]
    """How many faces the line has around it (2 along it), or `(along, around)`
    (default 24)."""


class Line3D(Cylinder):
    """A line in three dimensions: a thin cylinder from one point to another; checkered
    in two blues, and shaded by a three-dimensional scene's light, unless styled.

    An end may be a mobject: the line then starts (or ends) at its point farthest
    toward the other end (see [get_boundary_point][manimgx.Mobject.get_boundary_point]).

    Args:
        start: Where the line starts: a point, or a mobject.
        end: Where it ends: a point, or a mobject.
        thickness: Its radius, in scene units.
        resolution: How many faces it has around it (2 along it), or
            `(along, around)`.
        **kwargs: [Surface keywords][manimgx.mobjects.three_d.SurfaceLook]:
            `color` paints it all in one color; the style keywords.

    Examples:
        ```python
        import manimgx as m


        class Line3DExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=65 * m.DEGREES, theta=-45 * m.DEGREES)
                axes = m.ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-2, 2))
                line = m.Line3D(axes.c2p(-2, 0, 0), axes.c2p(1, 2, 1.5), thickness=0.05)
                self.add(axes, line.set_color(m.YELLOW))
        ```
    """

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        thickness: float = 0.02,
        resolution: int | Sequence[int] = 24,
        **kwargs: Unpack[SurfaceLook],
    ):
        color = kwargs.pop("color", None)
        self.thickness = thickness
        self.resolution = (2, resolution) if isinstance(resolution, int) else resolution
        self.set_start_and_end_attrs(start, end, **kwargs)
        if color is not None:
            self.set_color(color)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def set_start_and_end_attrs(
        self,
        start: Point3DLike | Mobject,
        end: Point3DLike | Mobject,
        **kwargs: Unpack[SurfaceLook],
    ) -> Self:
        """Make the line run from one point (or mobject) to another: the constructor
        calls it.

        It makes the line anew, as a cylinder of the line's thickness and resolution
        from `start` to `end`, styled by the keywords.

        Args:
            start: Where the line starts: a point, or a mobject.
            end: Where it ends: a point, or a mobject.
            **kwargs: [Surface keywords][manimgx.mobjects.three_d.SurfaceLook].
        """
        rough_start = self.pointify(start)
        rough_end = self.pointify(end)
        self.vect = rough_end - rough_start
        self.length = float(np.linalg.norm(self.vect))
        self.direction: Vector3D = normalize(self.vect)
        self.start = self.pointify(start, self.direction)
        self.end = self.pointify(end, -self.direction)
        super().__init__(
            height=self.length,
            radius=self.thickness,
            direction=self.direction,
            resolution=self.resolution,
            **kwargs,
        )
        self.shift((self.start + self.end) / 2)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def pointify(
        self, mob_or_point: Mobject | Point3DLike, direction: Vector3DLike | None = None
    ) -> Point3D:
        """Turn a point or a mobject into a point: a point as it is; a mobject's center,
        or its boundary point in a direction.

        Args:
            mob_or_point: The point, or the mobject.
            direction: The direction of the mobject's boundary point (see
                [get_boundary_point][manimgx.Mobject.get_boundary_point]); None for its
                center.

        Returns:
            The point, in scene coordinates.
        """
        if isinstance(mob_or_point, Mobject):
            return (
                mob_or_point.get_center()
                if direction is None
                else mob_or_point.get_boundary_point(direction)
            )
        return np.array(mob_or_point, dtype=float)

    @classmethod
    def parallel_to(
        cls,
        line: Line3D,
        point: Point3DLike = ORIGIN,
        length: float = 5,
        **kwargs: Unpack[Line3DOptions],
    ) -> Line3D:
        """Make a line parallel to another, through a point: `length` long, centered on
        the point.

        Args:
            line: The line to be parallel to.
            point: The point the new line is centered on.
            length: The new line's length, in scene units.
            **kwargs: [Line keywords][manimgx.mobjects.three_d.Line3DOptions]:
                `thickness`, `color`, ….

        Returns:
            A new line.

        Examples:
            ```python
            import manimgx as m


            class Line3DParallelToExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=60 * m.DEGREES, theta=-45 * m.DEGREES
                    )
                    line = m.Line3D(2 * m.RIGHT, m.UP + m.OUT, color=m.RED)
                    parallel = m.Line3D.parallel_to(line, color=m.YELLOW)
                    self.add(m.ThreeDAxes(), line, parallel)
            ```
        """
        np_point = np.asarray(point, dtype=float)
        vect = normalize(line.vect)
        return cls(np_point + vect * length / 2, np_point - vect * length / 2, **kwargs)

    @classmethod
    def perpendicular_to(
        cls,
        line: Line3D,
        point: Point3DLike = ORIGIN,
        length: float = 5,
        **kwargs: Unpack[Line3DOptions],
    ) -> Line3D:
        """Make a line perpendicular to another, through a point: in the plane of the
        line and the point, `length` long, centered on the point.

        A point on the line (which makes no plane with it) raises a ValueError.

        Args:
            line: The line to be perpendicular to.
            point: The point the new line is centered on, off the line.
            length: The new line's length, in scene units.
            **kwargs: [Line keywords][manimgx.mobjects.three_d.Line3DOptions]:
                `thickness`, `color`, ….

        Returns:
            A new line.

        Examples:
            ```python
            import manimgx as m


            class Line3DPerpendicularToExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=60 * m.DEGREES, theta=-45 * m.DEGREES
                    )
                    line = m.Line3D(2 * m.RIGHT, m.UP + m.OUT, color=m.RED)
                    perpendicular = m.Line3D.perpendicular_to(line, color=m.BLUE)
                    self.add(m.ThreeDAxes(), line, perpendicular)
            ```
        """
        np_point = np.asarray(point, dtype=float)
        norm = np.cross(line.vect, np_point - line.start)
        if np.linalg.norm(norm) == 0:
            raise ValueError("Could not find the perpendicular.")
        start, end = perpendicular_bisector([line.start, line.end], norm)
        vect = normalize(end - start)
        return cls(np_point + vect * length / 2, np_point - vect * length / 2, **kwargs)


class Arrow3D(Line3D):
    """An arrow in three dimensions: a thin cylinder from `start`, ending in a cone
    whose apex is at `end`; white unless given a color, shaded by a three-dimensional
    scene's light.

    Args:
        start: Where the arrow starts.
        end: Where its tip's apex is.
        thickness: The radius of its shaft, in scene units.
        height: The length of its tip, a [Cone][manimgx.Cone], in scene units.
        base_radius: The radius of its tip's base, in scene units.
        resolution: How many faces its shaft has around it (2 along it), or
            `(along, around)`.
        **kwargs: [Surface keywords][manimgx.mobjects.three_d.SurfaceLook]
            for the shaft and the tip: `color`, and the style keywords.

    Examples:
        ```python
        import manimgx as m


        class Arrow3DExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=65 * m.DEGREES, theta=-45 * m.DEGREES)
                axes = m.ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-2, 2))
                arrows = [
                    m.Arrow3D(axes.c2p(0, 0, 0), axes.c2p(*end), color=color)
                    for end, color in (
                        ((2, 0, 0), m.RED),
                        ((0, 2, 0), m.GREEN),
                        ((0, 0, 2), m.BLUE),
                        ((1.5, 1.5, 1.5), m.YELLOW),
                    )
                ]
                self.add(axes, *arrows)
        ```
    """

    def __init__(
        self,
        start: Point3DLike = LEFT,
        end: Point3DLike = RIGHT,
        thickness: float = 0.02,
        height: float = 0.3,
        base_radius: float = 0.08,
        resolution: int | tuple[int, int] = 24,
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        color = kwargs.pop("color", None) or WHITE
        start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        super().__init__(
            start=start,
            end=end - height * normalize(end - start),
            thickness=thickness,
            resolution=resolution,
            **kwargs,
        )
        self.cone = Cone(
            direction=self.direction, base_radius=base_radius, height=height, **kwargs
        )
        """Its tip: a [Cone][manimgx.Cone], its apex at the arrow's end."""
        self.cone.shift(end)
        self.end_point = VectorizedPoint(end)
        self.add(self.end_point, self.cone)
        self.set_color(color)


class Torus(Surface):
    """A torus: a tube around a circle in the xy-plane, centered at the origin;
    checkered in two blues and shaded by a three-dimensional scene's light, unless
    styled.

    It is a [Surface][manimgx.Surface] of u, the angle around its axis (z), and v, the
    angle around its tube: their ranges may cut out a part of it.

    Args:
        major_radius: The radius of the circle the tube runs around: from the torus's
            center to the middle of its tube, in scene units.
        minor_radius: The tube's radius, in scene units.
        u_range: The range of the angle around its axis, in radians: (0, τ) goes all
            the way around.
        v_range: The range of the angle around its tube, in radians.
        resolution: How many faces it has around its axis and around its tube: one
            number for both, or `(u, v)`; None for (24, 24).
        **kwargs: [Surface keywords][manimgx.mobjects.three_d.SurfaceLook]:
            `checkerboard_colors`, and the style keywords.

    Examples:
        ```python
        import manimgx as m


        class TorusExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=65 * m.DEGREES, theta=-60 * m.DEGREES)
                self.add(
                    m.Torus(major_radius=2, minor_radius=0.7).shift(3 * m.LEFT),
                    m.Torus(
                        major_radius=2,
                        minor_radius=0.7,
                        u_range=(0, 1.5 * m.PI),
                        checkerboard_colors=[m.ORANGE, m.YELLOW],
                    ).shift(3 * m.RIGHT),
                )
        ```
    """

    def __init__(
        self,
        major_radius: float = 3,
        minor_radius: float = 1,
        u_range: Sequence[float] = (0, TAU),
        v_range: Sequence[float] = (0, TAU),
        resolution: int | tuple[int, int] | None = None,
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        self.R = major_radius
        self.r = minor_radius
        super().__init__(
            self.func,
            u_range=u_range,
            v_range=v_range,
            resolution=resolution if resolution is not None else (24, 24),
            **kwargs,
        )

    def func(self, u: float, v: float) -> Point3D:
        """The torus's point, as it is made around the origin, at an angle around its
        axis and an angle around its tube.

        Args:
            u: The angle around the axis, in radians, counterclockwise from the x-axis.
            v: The angle around the tube, in radians: 0 on its inner side.

        Returns:
            The point, in scene coordinates.
        """
        return _revolve(self.R - self.r * np.cos(v), -self.r * np.sin(v), u)


class PolyhedronOptions(TypedDict, total=False, closed=True):
    """How a [Polyhedron][manimgx.Polyhedron]'s faces and its graph of vertices and
    edges look, for the solids that set their own vertices and faces
    ([Tetrahedron][manimgx.Tetrahedron], [ConvexHull3D][manimgx.ConvexHull3D], …)."""

    faces_config: Style | None
    """[Style keywords][manimgx.drawing.paint.Style] for the faces, over their defaults:
    half opaque, shaded by a three-dimensional scene's light (default None: none)."""
    graph_config: GraphOptions | None
    """[Graph keywords][manimgx.Graph] for the vertices and edges,
    over their defaults: [Dot3D][manimgx.Dot3D] vertices, invisible edges (default None:
    none)."""


class Polyhedron(VGroup):
    """A polyhedron: its faces, polygons through its vertices, and the graph of its
    vertices and edges; blue half-opaque faces with white dots at the vertices, shaded
    by a three-dimensional scene's light, unless styled.

    The faces are its [faces][manimgx.Polyhedron.faces], a group of
    [Polygon][manimgx.Polygon]s, whose outlines draw the edges; its
    [graph][manimgx.Polyhedron.graph] is a [Graph][manimgx.Graph] whose vertices are
    [Dot3D][manimgx.Dot3D]s, `graph[i]` the vertex of index i, and whose own edges are
    invisible unless configured. The faces follow the vertices: move a vertex, and an
    updater keeps the faces through it. Initial coordinates and graph options are
    construction inputs; later positions belong to the graph, and `faces_list`
    defines the faces.

    Args:
        vertex_coords: The vertices' points, in scene coordinates.
        faces_list: The faces, each a list of the indices of its vertices, in order
            around it.
        faces_config: [Style keywords][manimgx.drawing.paint.Style] for the faces, over
            their defaults (half opaque, shaded in 3D); None for none.
        graph_config: [Graph keywords][manimgx.Graph] for the
            vertices and edges, over their defaults ([Dot3D][manimgx.Dot3D] vertices,
            invisible edges); None for none.

    Examples:
        ```python
        import manimgx as m


        class PolyhedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                corners = [[1, 1, 0], [1, -1, 0], [-1, -1, 0], [-1, 1, 0], [0, 0, 2]]
                faces = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 1, 2, 3]]
                pyramid = m.Polyhedron(corners, faces).scale(1.5).shift(m.IN)
                self.add(pyramid)
                self.play(pyramid.graph[4].animate.move_to([1, 1, 2]), run_time=2)
        ```
    """

    def __init__(
        self,
        vertex_coords: Point3DLike_Array,
        faces_list: list[list[int]],
        faces_config: Style | None = None,
        graph_config: GraphOptions | None = None,
    ):
        super().__init__()
        self.faces_config = Style(fill_opacity=0.5, shade_in_3d=True) | (
            faces_config or Style()
        )
        graph_config = GraphOptions(
            vertex_type=Dot3D, edge_config={"stroke_opacity": 0}
        ) | (graph_config or GraphOptions())
        vertex_indices = list(range(len(vertex_coords)))
        layout: dict[Hashable, Point3D] = {
            i: np.asarray(p, dtype=float) for i, p in enumerate(vertex_coords)
        }
        self.faces_list = [list(face) for face in faces_list]
        """The faces, each a list of the indices of its vertices, as they were given."""
        face_coords = [[layout[j] for j in i] for i in faces_list]
        self.edges = self.get_edges(self.faces_list)
        """The edges, each a pair of vertex indices."""
        self.faces = self.create_faces(face_coords)
        """The faces: a group of [Polygon][manimgx.Polygon]s, in the order of
        `faces_list`."""
        self.graph = Graph(
            vertex_indices,
            self.edges,
            **(graph_config | GraphOptions(layout=layout)),
        )
        """The vertices and edges: a [Graph][manimgx.Graph], `graph[i]` the vertex of
        index i."""
        self.add(self.faces, self.graph)
        self.add_updater(self.update_faces)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_edges(self, faces_list: list[list[int]]) -> list[tuple[int, int]]:
        """Find the edges of faces: each two vertices next to each other around a face,
        each edge once.

        Args:
            faces_list: The faces, each a list of the indices of its vertices, in order
                around it.

        Returns:
            The edges, each a pair of vertex indices, in the order the faces first give
            them.
        """
        # each edge once (CE listed it once per face, doubling a translucent edge)
        edges: dict[frozenset[int], tuple[int, int]] = {}
        for face in faces_list:
            for edge in zip(face, face[1:] + face[:1], strict=True):
                edges.setdefault(frozenset(edge), edge)
        return list(edges.values())

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def create_faces(
        self, face_coords: Sequence[Sequence[Point3DLike]]
    ) -> VGroup[Polygon]:
        """Make faces: a polygon through each list of points, styled by the
        polyhedron's `faces_config`.

        Args:
            face_coords: The faces' corners, a list of points for each face.

        Returns:
            A new group of the polygons.
        """
        return VGroup[Polygon](
            *(Polygon(*face, **self.faces_config) for face in face_coords)
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def update_faces(self, m: Mobject) -> Self:
        """Put the faces back through the vertices, where they are now: the updater the
        polyhedron runs every frame.

        Args:
            m: The mobject the updater runs for (the polyhedron); unused.
        """
        for face, coords in zip(self.faces, self.extract_face_coords(), strict=True):
            face.set_points_as_corners([*coords, coords[0]])
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def extract_face_coords(self) -> list[list[Point3D]]:
        """The faces' corners where the vertices are now: the centers of the graph's
        vertices.

        Returns:
            A list of points for each face, in the order of `faces_list`.
        """
        vertices = [vertex.get_center() for vertex in self.graph.vertices.values()]
        return [[vertices[i] for i in face] for face in self.faces_list]


class Tetrahedron(Polyhedron):
    """A regular tetrahedron: four triangular faces, centered at the origin; a
    [Polyhedron][manimgx.Polyhedron], blue half-opaque faces with white dots at the
    vertices unless styled.

    Args:
        edge_length: The length of its edges, in scene units.
        **kwargs: [Polyhedron keywords][manimgx.mobjects.three_d.PolyhedronOptions]:
            `faces_config`, `graph_config`.

    Examples:
        ```python
        import manimgx as m


        class TetrahedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                self.add(m.Tetrahedron(edge_length=4))
        ```
    """

    def __init__(self, edge_length: float = 1, **kwargs: Unpack[PolyhedronOptions]):
        unit = edge_length * np.sqrt(2) / 4
        super().__init__(
            vertex_coords=[
                np.array([unit, unit, unit]),
                np.array([unit, -unit, -unit]),
                np.array([-unit, unit, -unit]),
                np.array([-unit, -unit, unit]),
            ],
            faces_list=[[0, 1, 2], [3, 0, 2], [0, 1, 3], [3, 1, 2]],
            **kwargs,
        )


class Octahedron(Polyhedron):
    """A regular octahedron: eight triangular faces, its vertices on the axes, centered
    at the origin; a [Polyhedron][manimgx.Polyhedron], blue half-opaque faces with
    white dots at the vertices unless styled.

    Args:
        edge_length: The length of its edges, in scene units.
        **kwargs: [Polyhedron keywords][manimgx.mobjects.three_d.PolyhedronOptions]:
            `faces_config`, `graph_config`.

    Examples:
        ```python
        import manimgx as m


        class OctahedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                octahedron = m.Octahedron(edge_length=3)
                octahedron.faces[2].set_color(m.YELLOW)
                octahedron.graph[0].set_color(m.RED)
                self.add(octahedron)
        ```
    """

    def __init__(self, edge_length: float = 1, **kwargs: Unpack[PolyhedronOptions]):
        unit = edge_length * np.sqrt(2) / 2
        super().__init__(
            vertex_coords=[
                np.array([unit, 0, 0]),
                np.array([-unit, 0, 0]),
                np.array([0, unit, 0]),
                np.array([0, -unit, 0]),
                np.array([0, 0, unit]),
                np.array([0, 0, -unit]),
            ],
            faces_list=[
                [2, 4, 1],
                [0, 4, 2],
                [4, 3, 0],
                [1, 3, 4],
                [3, 5, 0],
                [1, 5, 3],
                [2, 5, 1],
                [0, 5, 2],
            ],
            **kwargs,
        )


class Icosahedron(Polyhedron):
    """A regular icosahedron: twenty triangular faces, centered at the origin; a
    [Polyhedron][manimgx.Polyhedron], blue half-opaque faces with white dots at the
    vertices unless styled.

    Args:
        edge_length: The length of its edges, in scene units.
        **kwargs: [Polyhedron keywords][manimgx.mobjects.three_d.PolyhedronOptions]:
            `faces_config`, `graph_config`.

    Examples:
        ```python
        import manimgx as m


        class IcosahedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                self.add(m.Icosahedron(edge_length=2, faces_config={"color": m.TEAL}))
        ```
    """

    def __init__(self, edge_length: float = 1, **kwargs: Unpack[PolyhedronOptions]):
        unit_a = edge_length * ((1 + np.sqrt(5)) / 4)
        unit_b = edge_length * (1 / 2)
        super().__init__(
            vertex_coords=[
                np.array([0, unit_b, unit_a]),
                np.array([0, -unit_b, unit_a]),
                np.array([0, unit_b, -unit_a]),
                np.array([0, -unit_b, -unit_a]),
                np.array([unit_b, unit_a, 0]),
                np.array([unit_b, -unit_a, 0]),
                np.array([-unit_b, unit_a, 0]),
                np.array([-unit_b, -unit_a, 0]),
                np.array([unit_a, 0, unit_b]),
                np.array([unit_a, 0, -unit_b]),
                np.array([-unit_a, 0, unit_b]),
                np.array([-unit_a, 0, -unit_b]),
            ],
            faces_list=[
                [1, 8, 0],
                [1, 5, 7],
                [8, 5, 1],
                [7, 3, 5],
                [5, 9, 3],
                [8, 9, 5],
                [3, 2, 9],
                [9, 4, 2],
                [8, 4, 9],
                [0, 4, 8],
                [6, 4, 0],
                [6, 2, 4],
                [11, 2, 6],
                [3, 11, 2],
                [0, 6, 10],
                [10, 1, 0],
                [10, 7, 1],
                [11, 7, 3],
                [10, 11, 7],
                [10, 11, 6],
            ],
            **kwargs,
        )


class Dodecahedron(Polyhedron):
    """A regular dodecahedron: twelve pentagonal faces, centered at the origin; a
    [Polyhedron][manimgx.Polyhedron], blue half-opaque faces with white dots at the
    vertices unless styled.

    Args:
        edge_length: The length of its edges, in scene units.
        **kwargs: [Polyhedron keywords][manimgx.mobjects.three_d.PolyhedronOptions]:
            `faces_config`, `graph_config`.

    Examples:
        ```python
        import manimgx as m


        class DodecahedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                self.add(
                    m.Dodecahedron(edge_length=1.5, faces_config={"color": m.PURPLE})
                )
        ```
    """

    def __init__(self, edge_length: float = 1, **kwargs: Unpack[PolyhedronOptions]):
        unit_a = edge_length * ((1 + np.sqrt(5)) / 4)
        unit_b = edge_length * ((3 + np.sqrt(5)) / 4)
        unit_c = edge_length * (1 / 2)
        super().__init__(
            vertex_coords=[
                np.array([unit_a, unit_a, unit_a]),
                np.array([unit_a, unit_a, -unit_a]),
                np.array([unit_a, -unit_a, unit_a]),
                np.array([unit_a, -unit_a, -unit_a]),
                np.array([-unit_a, unit_a, unit_a]),
                np.array([-unit_a, unit_a, -unit_a]),
                np.array([-unit_a, -unit_a, unit_a]),
                np.array([-unit_a, -unit_a, -unit_a]),
                np.array([0, unit_c, unit_b]),
                np.array([0, unit_c, -unit_b]),
                np.array([0, -unit_c, -unit_b]),
                np.array([0, -unit_c, unit_b]),
                np.array([unit_c, unit_b, 0]),
                np.array([-unit_c, unit_b, 0]),
                np.array([unit_c, -unit_b, 0]),
                np.array([-unit_c, -unit_b, 0]),
                np.array([unit_b, 0, unit_c]),
                np.array([-unit_b, 0, unit_c]),
                np.array([unit_b, 0, -unit_c]),
                np.array([-unit_b, 0, -unit_c]),
            ],
            faces_list=[
                [18, 16, 0, 12, 1],
                [3, 18, 16, 2, 14],
                [3, 10, 9, 1, 18],
                [1, 9, 5, 13, 12],
                [0, 8, 4, 13, 12],
                [2, 16, 0, 8, 11],
                [4, 17, 6, 11, 8],
                [17, 19, 5, 13, 4],
                [19, 7, 15, 6, 17],
                [6, 15, 14, 2, 11],
                [19, 5, 9, 10, 7],
                [7, 10, 3, 14, 15],
            ],
            **kwargs,
        )


class ConvexHull3D(Polyhedron):
    """The convex hull of points in three dimensions: the smallest convex polyhedron
    around them, its faces triangles; a [Polyhedron][manimgx.Polyhedron], blue
    half-opaque faces with white dots at the vertices unless styled.

    Its vertices are the points on the hull (those inside are left out), and its faces
    are wound counterclockwise, seen from outside. Fewer than four points raise a
    ValueError.

    Args:
        *points: The points, in scene coordinates.
        tolerance: How far outside a face a point must be to count as beyond it, in
            scene units.
        **kwargs: [Polyhedron keywords][manimgx.mobjects.three_d.PolyhedronOptions]:
            `faces_config`, `graph_config`.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ConvexHull3DExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                points = np.random.default_rng(1).uniform(-2, 2, size=(30, 3))
                hull = m.ConvexHull3D(*points, faces_config={"color": m.GREEN})
                self.add(hull, *(m.Dot3D(p, color=m.YELLOW) for p in points))
        ```
    """

    def __init__(
        self,
        *points: Point3DLike,
        tolerance: float = 1e-05,
        **kwargs: Unpack[PolyhedronOptions],
    ):
        array = np.array(points, dtype=float)
        hull = QuickHull(tolerance)
        hull.build(array)
        # In the hull's own order: CE iterated hash sets of point bytes, whose order changes
        # from process to process (salted hashing), and so did faces, vertex ids and draw order.
        index: dict[bytes, int] = {}
        vertices: list[Point3D] = []
        faces: list[list[int]] = []
        for facet in dict.fromkeys(hull.facets):
            if facet in hull.removed:
                continue
            a, b, c = facet.coordinates
            corners = (
                (a, b, c)
                if np.dot(np.cross(b - a, c - a), facet.normal) > 0
                else (a, c, b)
            )
            for point in corners:  # wound counterclockwise seen from outside
                if point.tobytes() not in index:
                    index[point.tobytes()] = len(vertices)
                    vertices.append(point)
            faces.append([index[point.tobytes()] for point in corners])
        super().__init__(vertex_coords=vertices, faces_list=faces, **kwargs)
