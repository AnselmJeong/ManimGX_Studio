import math

import numpy as np

import manimgx as m

_COS60 = math.cos(math.pi / 3)
_SIN60 = math.sin(math.pi / 3)


def koch(start: np.ndarray, end: np.ndarray, order: int) -> list[np.ndarray]:
    if order == 0:
        return [start, end]
    diff = end - start
    b = start + diff / 3
    c = start + 2 * diff / 3
    seg = c - b
    apex = b + np.array(
        [
            _COS60 * seg[0] - _SIN60 * seg[1],
            _SIN60 * seg[0] + _COS60 * seg[1],
            0.0,
        ]
    )
    pts: list[np.ndarray] = []
    pts.extend(koch(start, b, order - 1)[:-1])
    pts.extend(koch(b, apex, order - 1)[:-1])
    pts.extend(koch(apex, c, order - 1)[:-1])
    pts.extend(koch(c, end, order - 1))
    return pts


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex(
            "Box counting: ",
            "$N(\\epsilon) \\sim \\epsilon^{-d}$",
        ).to_edge(m.UP, buff=0.4)
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        start = np.array([-4.0, -1.5, 0.0])
        end = np.array([4.0, -1.5, 0.0])
        pts = koch(start, end, 4)
        curve = m.VMobject(stroke_color=m.YELLOW, stroke_width=2)
        curve.set_points_as_corners(pts)
        self.play(m.Create(curve), run_time=1.5)

        for grid_size, color in [(2.0, m.BLUE), (1.0, m.GREEN), (0.5, m.RED)]:
            lines = m.VGroup()
            for x in np.arange(-4.0, 4.01, grid_size):
                lines.add(
                    m.Line(
                        [x, -1.5, 0],
                        [x, 2.0, 0],
                        color=color,
                        stroke_opacity=0.45,
                        stroke_width=1,
                    )
                )
            for y in np.arange(-1.5, 2.01, grid_size):
                lines.add(
                    m.Line(
                        [-4.0, y, 0],
                        [4.0, y, 0],
                        color=color,
                        stroke_opacity=0.45,
                        stroke_width=1,
                    )
                )
            self.play(m.FadeIn(lines), run_time=0.6)
            self.wait(0.6)
            self.play(m.FadeOut(lines), run_time=0.4)

        self.wait(1.0)
