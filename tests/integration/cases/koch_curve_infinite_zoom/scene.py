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
        title = m.Tex("Koch curve, orders 0–5").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        start = np.array([-4.5, -0.5, 0.0])
        end = np.array([4.5, -0.5, 0.0])

        curve = None
        order_label = None
        for order in range(6):
            pts = koch(start, end, order)
            new_curve = m.VMobject(
                stroke_color=m.YELLOW,
                stroke_width=max(1.0, 3.0 - 0.4 * order),
            )
            new_curve.set_points_as_corners(pts)
            new_label = m.MathTex(f"\\text{{order }} {order}").to_corner(m.UR, buff=0.5)

            if curve is None or order_label is None:
                curve = new_curve
                order_label = new_label
                self.play(m.Create(curve), m.Write(order_label))
            else:
                self.play(
                    m.Transform(curve, new_curve),
                    m.Transform(order_label, new_label),
                    run_time=1.2,
                )
            self.wait(0.4)
        self.wait(1.5)
