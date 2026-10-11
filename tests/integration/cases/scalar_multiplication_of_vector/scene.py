import numpy as np

import manimgx as m

V = np.array([2.0, 1.0, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-3, 3, 1],
            x_length=12,
            y_length=7,
        )
        self.play(m.Create(plane), run_time=0.8)

        origin = plane.coords_to_point(0, 0)
        arrow = m.Arrow(
            origin,
            plane.coords_to_point(V[0], V[1]),
            color=m.YELLOW,
            buff=0,
            stroke_width=5,
        )
        label = m.MathTex("\\vec{v}", color=m.YELLOW).next_to(
            arrow.get_end(), m.UP, buff=0.15
        )
        self.play(m.GrowArrow(arrow), m.Write(label))
        self.wait(0.4)

        steps = [(2.0, m.BLUE), (0.5, m.GREEN), (-1.0, m.RED)]
        for k, color in steps:
            scaled = k * V
            new_arrow = m.Arrow(
                origin,
                plane.coords_to_point(scaled[0], scaled[1]),
                color=color,
                buff=0,
                stroke_width=5,
            )
            side = m.UP if k > 0 else m.DOWN
            new_label = m.MathTex(
                f"{k:g}",
                "\\vec{v}",
                color=color,
            ).next_to(new_arrow.get_end(), side, buff=0.15)
            self.play(
                m.Transform(arrow, new_arrow),
                m.Transform(label, new_label),
                run_time=1.3,
            )
            self.wait(0.6)
        self.wait(1.2)
