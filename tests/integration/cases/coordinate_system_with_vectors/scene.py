import numpy as np

import manimgx as m

V = np.array([3.0, 2.0, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-1, 5, 1],
            y_range=[-1, 4, 1],
            x_length=10,
            y_length=8,
        )
        self.play(m.Create(plane), run_time=0.9)

        origin = plane.coords_to_point(0, 0)
        v_end = plane.coords_to_point(V[0], V[1])
        x_proj = plane.coords_to_point(V[0], 0)
        y_proj = plane.coords_to_point(0, V[1])

        arrow = m.Arrow(origin, v_end, color=m.YELLOW, buff=0, stroke_width=5)
        v_label = (
            m.MathTex(
                "\\vec{v} = \\begin{pmatrix} 3 \\\\ 2 \\end{pmatrix}",
                color=m.YELLOW,
            )
            .scale(0.85)
            .next_to(arrow.get_end(), m.UR, buff=0.2)
        )
        self.play(m.GrowArrow(arrow), m.Write(v_label))
        self.wait(0.5)

        x_dash = m.DashedLine(v_end, x_proj, color=m.BLUE, stroke_width=2.5)
        y_dash = m.DashedLine(v_end, y_proj, color=m.GREEN, stroke_width=2.5)
        x_coord = (
            m.MathTex("3", color=m.BLUE).scale(0.9).next_to(x_proj, m.DOWN, buff=0.25)
        )
        y_coord = (
            m.MathTex("2", color=m.GREEN).scale(0.9).next_to(y_proj, m.LEFT, buff=0.25)
        )

        self.play(m.Create(x_dash), m.Create(y_dash))
        self.play(m.Write(x_coord), m.Write(y_coord))
        self.wait(2.0)
