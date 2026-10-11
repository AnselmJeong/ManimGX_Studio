"""Lights: what lights the mobjects that have a [material][manimgx.Material] in a
three-dimensional scene. A light is a mobject that draws nothing: placed, moved and
animated like any, and a scene's lights are the ones in it. Its intensity is what a white
matte surface shows: 1 makes such a surface facing the light white."""

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "AmbientLight",
    "EnvironmentLight",
    "Light",
    "PointLight",
    "SpotLight",
    "SunLight",
]

import functools
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Unpack

import numpy as np

from manimgx import _engine
from manimgx.caches import forgets
from manimgx.constants import LEFT, ORIGIN, OUT, PI, RIGHT, UP
from manimgx.drawing.paint import WHITE, Look, ManimColor, ParsableManimColor
from manimgx.mobject import VectorizedPoint

if TYPE_CHECKING:
    from manimgx.typing import Point3DLike


class Light(VectorizedPoint):
    """A light: its color and how bright it is, at its point (each kind reads the point its
    own way).

    Args:
        location: Where it is, in scene coordinates.
        color: Its color.
        intensity: How bright it is: 1 makes a white matte surface facing it white.
        **kwargs: [Look keywords][manimgx.drawing.paint.Look] (a name, a z-index).
    """

    kind: ClassVar[int] = 0
    """How the renderer reads it: 0 ambient, 1 sun, 2 point, 3 spot, 4 environment."""

    def __init__(
        self,
        location: Point3DLike = ORIGIN,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        **kwargs: Unpack[Look],
    ) -> None:
        self.light_color = ManimColor(color)
        self.intensity = intensity
        super().__init__(location, **kwargs)


class AmbientLight(Light):
    """Light from every direction alike: the sky, or a room's light come back from its walls.
    It lights what no other light reaches, so that nothing goes black.

    Args:
        color: Its color.
        intensity: How bright it is: 1 makes a white matte surface white, from every side.
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class AmbientLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-40 * m.DEGREES)
                self.add(m.AmbientLight(m.BLUE_A, intensity=0.4))
                self.add(m.Sphere(resolution=(48, 48)).set_material(m.Material()))
        ```
    """

    kind: ClassVar[int] = 0

    def __init__(
        self,
        color: ParsableManimColor = WHITE,
        intensity: float = 0.1,
        **kwargs: Unpack[Look],
    ) -> None:
        super().__init__(ORIGIN, color, intensity, **kwargs)


class SunLight(Light):
    """Parallel light from far away, coming from where its point is as seen from the origin:
    move the point around the origin to turn the light.

    Args:
        location: Where the light comes from: its direction from the origin.
        color: Its color.
        intensity: How bright it is: 1 makes a white matte surface facing it white.
        shadows: Whether what it lights casts shadows (on the mobjects with a material).
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class SunLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=65 * m.DEGREES, theta=-45 * m.DEGREES)
                sun = m.SunLight(5 * m.RIGHT + 3 * m.OUT)
                self.add(sun, m.AmbientLight(intensity=0.15))
                self.add(m.Sphere(resolution=(48, 48)).set_material(m.Material()))
                self.play(
                    m.Rotate(sun, m.PI, axis=m.OUT, about_point=m.ORIGIN), run_time=3
                )
        ```
    """

    kind: ClassVar[int] = 1

    def __init__(
        self,
        location: Point3DLike = 4 * UP + 3 * LEFT + 5 * OUT,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        shadows: bool = True,
        **kwargs: Unpack[Look],
    ) -> None:
        self.shadows = shadows
        super().__init__(location, color, intensity, **kwargs)


class PointLight(Light):
    """Light from its point in every direction, a bulb's: it falls off with the square of the
    distance, and fades out entirely by `radius`.

    Args:
        location: Where it is, in scene coordinates.
        color: Its color.
        intensity: How bright it is one unit away: 1 makes a white matte surface facing it
            there white.
        radius: How far its light reaches, in scene units.
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class PointLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-30 * m.DEGREES)
                lamp = m.PointLight(2 * m.OUT + 2 * m.LEFT, m.ORANGE, intensity=6)
                self.add(lamp, m.AmbientLight(intensity=0.05))
                floor = m.Surface(
                    lambda u, v: [u, v, -1], u_range=[-4, 4], v_range=[-4, 4]
                )
                self.add(floor.set_material(m.Material(roughness=0.4)))
                self.play(lamp.animate.shift(4 * m.RIGHT), run_time=3)
        ```
    """

    kind: ClassVar[int] = 2

    def __init__(
        self,
        location: Point3DLike = 3 * OUT,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        radius: float = 20.0,
        **kwargs: Unpack[Look],
    ) -> None:
        self.radius = radius
        super().__init__(location, color, intensity, **kwargs)


class SpotLight(PointLight):
    """A point light's cone: from its point to the point `toward`, as wide as `angle` either
    side of its axis, its edge softened over the outer `softness` of the angle.

    Args:
        location: Where it is, in scene coordinates.
        toward: The point it shines toward.
        color: Its color.
        intensity: How bright it is one unit away, on its axis.
        radius: How far its light reaches, in scene units.
        angle: Half its cone's opening, in radians.
        softness: The fraction of `angle`, at the cone's edge, over which its light fades.
        shadows: Whether what it lights casts shadows (on the mobjects with a material).
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class SpotLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=60 * m.DEGREES, theta=-60 * m.DEGREES)
                self.add(
                    m.SpotLight(
                        4 * m.OUT, toward=m.ORIGIN, intensity=20, angle=m.PI / 8
                    )
                )
                floor = m.Surface(
                    lambda u, v: [u, v, 0], u_range=[-4, 4], v_range=[-4, 4]
                )
                self.add(floor.set_material(m.Material(roughness=0.7)))
        ```
    """

    kind: ClassVar[int] = 3

    def __init__(
        self,
        location: Point3DLike = 4 * OUT,
        toward: Point3DLike = ORIGIN,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        radius: float = 20.0,
        angle: float = PI / 6,
        softness: float = 0.2,
        shadows: bool = True,
        **kwargs: Unpack[Look],
    ) -> None:
        self.shadows = shadows
        self.toward = np.asarray(toward, dtype=float)
        self.angle = angle
        self.softness = softness
        super().__init__(location, color, intensity, radius, **kwargs)


@dataclass(frozen=True, slots=True, eq=False)
class Picture:
    """An environment's picture as the engine takes it: equirectangular (its width twice its
    height), each pixel RGBE (a byte of red, green, blue and a shared exponent), row by row
    from the top; `id` names it to the player (the views that show it carry the id)."""

    id: int
    width: int
    height: int
    rgbe: bytes


_PICTURE_IDS = itertools.count(1)  # (0: the studio; a view carries an id as a float32)


@forgets
@functools.lru_cache(maxsize=4)
def _picture(data: bytes) -> Picture:
    """A Radiance picture's immutable contents, decoded once while remembered (the engine
    halves it until no wider than 4096)."""
    width, height, rgbe = _engine.read_hdr(data)
    return Picture(next(_PICTURE_IDS), width, height, bytes(rgbe))


class EnvironmentLight(Light):
    """Light from all around: a picture of the surroundings, each direction's light the
    picture's there, as at the place it was taken. Metals mirror it, rough ones blur it,
    and matte surfaces take its light from every side. A sun in the picture lights as a
    sun does: its light comes from its direction alone, and it casts shadows. A scene
    lights by one picture (a second environment light shows the first's).

    The picture is a panorama (equirectangular: a Radiance `.hdr` file, its width twice
    its height), its up the scene's up (`OUT`), its centre seen looking along `RIGHT`.
    Rotate the light to turn its surroundings: its points are where it is and, a unit
    away, its picture's `RIGHT` and up.

    Args:
        picture: A Radiance (`.hdr`) file's path; None, a studio's (built in: a dim room
            with softboxes: a key light where Manim's light source is, a fill, a strip for
            rims, a light overhead).
        color: Its tint: the picture's light times this color.
        intensity: How bright it is: the picture's light times this (a picture of light
            1 all around makes a white matte surface white).
        shadows: Whether its picture's sun, if it has one, casts shadows (on the mobjects
            with a material).
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class EnvironmentLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-50 * m.DEGREES)
                studio = m.EnvironmentLight()
                self.add(studio)
                for i, roughness in enumerate([0.05, 0.35, 0.8]):
                    ball = m.Sphere(radius=0.8, resolution=(64, 64)).set_color(m.GREY_A)
                    ball.set_material(m.Material(metallic=1, roughness=roughness))
                    self.add(ball.shift(2 * (i - 1) * m.RIGHT))
                self.play(m.Rotate(studio, m.TAU, axis=m.OUT), run_time=4)
        ```
    """

    kind: ClassVar[int] = 4
    shared: ClassVar[frozenset[str]] = Light.shared | {"picture"}  # a value, read once

    def __init__(
        self,
        picture: str | Path | None = None,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        shadows: bool = True,
        **kwargs: Unpack[Look],
    ) -> None:
        # (None: the studio, which the engine makes)
        self.picture = None if picture is None else _picture(Path(picture).read_bytes())
        self.shadows = shadows
        super().__init__(ORIGIN, color, intensity, **kwargs)
        # its picture's right and up, a unit from its point: turned with it
        self.add(VectorizedPoint(RIGHT), VectorizedPoint(OUT))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def axes(self) -> tuple[np.ndarray, np.ndarray]:
        """Its picture's `RIGHT` and up in the scene, as it is turned: unit vectors, at a right
        angle."""
        origin = self.points[0]
        right, up = (s.points[0] - origin for s in self.submobjects[:2])
        up = up / max(float(np.linalg.norm(up)), 1e-9)
        right = right - up * float(right @ up)
        return right / max(float(np.linalg.norm(right)), 1e-9), up
