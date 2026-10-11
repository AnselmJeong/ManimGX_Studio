import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("1D exponential vs 2D linear system").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        axes = m.Axes(
            x_range=[0, 3, 1],
            y_range=[0, 8, 2],
            x_length=3.5,
            y_length=2.5,
            tips=False,
            axis_config={"include_numbers": False, "stroke_width": 1.5},
        ).shift(m.LEFT * 3.5 + m.DOWN * 0.5)
        curve = axes.plot(lambda x: math.exp(x), color=m.BLUE, x_range=[0, 3])
        l_label = (
            m.MathTex("\\dot x = rx", color=m.BLUE)
            .scale(0.8)
            .next_to(axes, m.UP, buff=0.2)
        )
        self.play(m.Create(axes), m.Write(l_label))
        self.play(m.Create(curve), run_time=1.5)

        plane = m.NumberPlane(
            x_range=[-2.5, 2.5, 1],
            y_range=[-2.0, 2.0, 1],
            x_length=3.5,
            y_length=2.5,
            background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
        ).shift(m.RIGHT * 3.0 + m.DOWN * 0.5)
        r_label = (
            m.MathTex("\\dot{\\mathbf v} = M\\,\\mathbf v", color=m.YELLOW)
            .scale(0.8)
            .next_to(plane, m.UP, buff=0.2)
        )
        self.play(m.Create(plane), m.Write(r_label))

        traj_pts: list[np.ndarray] = [np.array([0.3, 0.0, 0.0])]
        for _ in range(120):
            p = traj_pts[-1]
            v = np.array([0.3 * p[0] - 0.5 * p[1], 0.5 * p[0] + 0.3 * p[1], 0.0])
            traj_pts.append(p + 0.04 * v)
        spiral = m.VMobject(stroke_color=m.YELLOW, stroke_width=3.0)
        spiral.set_points_as_corners(
            [plane.coords_to_point(p[0], p[1]) for p in traj_pts]
        )
        self.play(m.Create(spiral), run_time=2.0)
        self.wait(2.0)
