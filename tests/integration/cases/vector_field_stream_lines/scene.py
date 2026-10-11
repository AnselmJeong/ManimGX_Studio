import numpy as np

import manimgx as m


def field(x: float, y: float) -> np.ndarray:
    return np.array([-y, x, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Rotational vector field").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        plane = m.NumberPlane(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            x_length=10,
            y_length=7,
        )
        self.add(plane)

        arrows = m.VGroup()
        for x in np.arange(-2.5, 2.51, 0.5):
            for y in np.arange(-1.5, 1.51, 0.5):
                vec = field(x, y)
                norm = np.linalg.norm(vec)
                if norm < 0.05:
                    continue
                scale = 0.4 / max(norm, 0.3)
                start = plane.coords_to_point(x, y)
                end = plane.coords_to_point(x + scale * vec[0], y + scale * vec[1])
                arrows.add(
                    m.Arrow(
                        start,
                        end,
                        color=m.BLUE,
                        buff=0,
                        stroke_width=2,
                        max_tip_length_to_length_ratio=0.3,
                    ),
                )
        self.play(
            m.LaggedStart(*[m.GrowArrow(a) for a in arrows], lag_ratio=0.005),
            run_time=2.5,
        )
        self.wait(2.0)
