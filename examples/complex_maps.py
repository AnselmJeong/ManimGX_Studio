"""Complex functions bend the plane.

A complex function sends each point z of the plane to a point f(z). Carry a grid along and the
function's shape appears. z² doubles every angle about the origin and squares every distance:
the grid's lines become parabolas. e^{x+iy} = e^x · e^{iy}, so a vertical line wraps onto a
circle and a horizontal line straightens into a ray. sin z bends the lines into ellipses and
hyperbolas that share two foci. Whatever the function, the bent lines still cross at right
angles: a complex function keeps angles wherever its derivative isn't 0.
"""

from collections.abc import Callable

import numpy as np

import manimgx as m

WALL = 2.4  # the README wall's 5 seconds start here
UNIT = 1.75  # screen units per unit of the plane
HALF = 2.0  # the grid covers [−HALF, HALF] in both directions
STEP = 0.25  # between its lines
SAMPLES = 240  # points along each line
REAL, IMAGINARY = m.BLUE_D, m.YELLOW


def grid() -> tuple[m.VGroup, list[np.ndarray]]:
    """The grid's lines, and each line's points as complex numbers."""
    lines = m.VGroup()
    points: list[np.ndarray] = []
    run = np.linspace(-HALF, HALF, SAMPLES)
    for k in np.arange(-HALF, HALF + STEP / 2, STEP):
        for z, color in ((k + 1j * run, REAL), (run + 1j * k, IMAGINARY)):
            axis = abs(k) < 1e-9
            line = m.VMobject(
                stroke_color=m.WHITE if axis else color,
                stroke_width=4.5 if axis else 3,
            )
            lines.add(line)
            points.append(z)
    return lines, points


def place(
    lines: m.VGroup,
    points: list[np.ndarray],
    f: Callable[[np.ndarray], np.ndarray],
    t: float,
) -> None:
    """Each line at t of the way from z to f(z)."""
    for line, z in zip(lines, points, strict=True):
        assert isinstance(line, m.VMobject)
        w = (1 - t) * z + t * f(z)
        line.set_points_as_corners(
            UNIT * np.stack([w.real, w.imag, np.zeros(len(w))], axis=1)
        )


class ComplexMaps(m.Scene):
    def construct(self) -> None:
        lines, points = grid()
        place(lines, points, lambda z: z, 0)
        ghost = lines.copy().set_stroke(opacity=0.18)  # where the lines started
        corner = np.array([-6.6, 3.45, 0.0])
        shown = {"label": m.MathTex("f(z) = z", font_size=60)}
        shown["label"].move_to(corner, aligned_edge=m.LEFT)

        def relabel(tex: str, seconds: float) -> None:
            formula = m.MathTex(tex, font_size=60).move_to(corner, aligned_edge=m.LEFT)
            self.play(m.TransformMatchingTex(shown["label"], formula), run_time=seconds)
            shown["label"] = formula

        def bend(
            f: Callable[[np.ndarray], np.ndarray], back: bool, seconds: float
        ) -> None:
            self.play(
                m.UpdateFromAlphaFunc(
                    lines, lambda mob, a: place(mob, points, f, 1 - a if back else a)
                ),
                run_time=seconds,
            )

        def show(f: Callable[[np.ndarray], np.ndarray], tex: str) -> None:
            relabel(tex, 0.8)
            bend(f, back=False, seconds=3)
            self.wait(1.2)
            bend(f, back=True, seconds=2)
            relabel("f(z) = z", 0.6)

        self.add(ghost)
        self.play(
            m.Create(lines, lag_ratio=0.01), m.Write(shown["label"]), run_time=1.5
        )
        show(lambda z: z * z, "f(z) = z^2")
        show(np.exp, "f(z) = e^z")
        show(np.sin, r"f(z) = \sin z")
        self.wait(1)


if __name__ == "__main__":
    ComplexMaps().render("complex_maps.mp4")
