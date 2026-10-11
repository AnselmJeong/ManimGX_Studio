import numpy as np

import manimgx as m


def field(p: np.ndarray) -> np.ndarray:
    x, y = p[0], p[1]
    return np.array([0.4 * y, -0.4 * x, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("$\\dot{\\mathbf v} = M\\,\\mathbf v$ vector field").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        plane = (
            m.NumberPlane(
                x_range=[-4, 4, 1],
                y_range=[-2.6, 2.6, 1],
                background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
            )
            .scale(0.85)
            .shift(m.DOWN * 0.3)
        )
        self.play(m.Create(plane))

        arrows = m.VGroup()
        for x in np.arange(-3.2, 3.21, 0.8):
            for y in np.arange(-2.0, 2.01, 0.8):
                start = plane.coords_to_point(x, y)
                vec = field(np.array([x, y, 0.0]))
                end = plane.coords_to_point(x + vec[0], y + vec[1])
                arrows.add(
                    m.Arrow(
                        start,
                        end,
                        color=m.BLUE,
                        stroke_width=2.0,
                        buff=0,
                        max_tip_length_to_length_ratio=0.3,
                    )
                )
        self.play(m.LaggedStartMap(m.FadeIn, arrows, lag_ratio=0.005, run_time=1.5))

        traj_pts = [np.array([2.0, 0.0, 0.0])]
        for _ in range(150):
            p = traj_pts[-1]
            v = field(p)
            traj_pts.append(p + 0.05 * v)
        path = m.VMobject(stroke_color=m.YELLOW, stroke_width=3.5)
        path.set_points_as_corners(
            [plane.coords_to_point(p[0], p[1]) for p in traj_pts]
        )
        self.play(m.Create(path), run_time=2.5)
        self.wait(1.5)
