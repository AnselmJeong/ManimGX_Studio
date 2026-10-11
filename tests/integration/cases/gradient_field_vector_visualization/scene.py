import numpy as np

import manimgx as m


def grad_f(x: float, y: float) -> np.ndarray:
    return np.array([0.5 * x, 0.5 * y])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=8,
            y_length=8,
        )
        self.add(plane)

        title = (
            m.Tex(
                "Gradient field of ",
                "$f(x,y) = \\tfrac{1}{4}(x^2 + y^2)$",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        arrows = m.VGroup()
        for x in np.arange(-2.0, 2.01, 0.7):
            for y in np.arange(-2.0, 2.01, 0.7):
                g = grad_f(x, y)
                start = plane.coords_to_point(x, y)
                end = plane.coords_to_point(x + 0.6 * g[0], y + 0.6 * g[1])
                if np.linalg.norm(end - start) > 0.05:
                    arrows.add(
                        m.Arrow(
                            start,
                            end,
                            color=m.YELLOW,
                            buff=0,
                            stroke_width=2.5,
                            max_tip_length_to_length_ratio=0.3,
                        )
                    )
        self.play(
            m.LaggedStart(*[m.GrowArrow(a) for a in arrows], lag_ratio=0.01),
            run_time=2.5,
        )
        self.wait(2.0)
