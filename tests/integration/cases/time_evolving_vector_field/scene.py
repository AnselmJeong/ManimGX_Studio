import math

import numpy as np

import manimgx as m


def field(x: float, y: float, t: float) -> np.ndarray:
    return np.array(
        [
            math.cos(t) * x + math.sin(t) * y,
            -math.sin(t) * x + math.cos(t) * y,
            0.0,
        ]
    )


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Time-evolving vector field").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        plane = m.NumberPlane(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            x_length=10,
            y_length=7,
        )
        self.add(plane)

        t = m.ValueTracker(0.0)

        def make_arrows() -> m.VGroup:
            arrows = m.VGroup()
            time = t.get_value()
            for x in np.arange(-2.5, 2.51, 0.6):
                for y in np.arange(-1.5, 1.51, 0.6):
                    vec = field(x, y, time)
                    norm = np.linalg.norm(vec)
                    if norm < 0.05:
                        continue
                    scale = 0.3 / max(norm, 0.5)
                    start = plane.coords_to_point(x, y)
                    end = plane.coords_to_point(x + scale * vec[0], y + scale * vec[1])
                    arrows.add(
                        m.Arrow(
                            start,
                            end,
                            color=m.YELLOW,
                            buff=0,
                            stroke_width=2,
                            max_tip_length_to_length_ratio=0.3,
                        ),
                    )
            return arrows

        self.add(m.always_redraw(make_arrows))
        self.play(t.animate.set_value(2 * math.pi), run_time=5.0, rate_func=m.linear)
        self.wait(1.0)
