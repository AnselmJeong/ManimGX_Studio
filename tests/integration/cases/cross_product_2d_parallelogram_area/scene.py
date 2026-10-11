import numpy as np

import manimgx as m

V = np.array([3.0, 1.0])
W = np.array([1.0, 2.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-1, 5, 1],
            y_range=[-1, 4, 1],
            x_length=10,
            y_length=8,
        )
        self.add(plane)

        origin = plane.coords_to_point(0, 0)
        v_arr = m.Arrow(
            origin,
            plane.coords_to_point(V[0], V[1]),
            color=m.GREEN,
            buff=0,
            stroke_width=5,
        )
        w_arr = m.Arrow(
            origin,
            plane.coords_to_point(W[0], W[1]),
            color=m.RED,
            buff=0,
            stroke_width=5,
        )
        v_label = m.MathTex("\\vec{v}", color=m.GREEN).next_to(
            v_arr.get_end(), m.UP, buff=0.1
        )
        w_label = m.MathTex("\\vec{w}", color=m.RED).next_to(
            w_arr.get_end(), m.UR, buff=0.1
        )
        self.play(
            m.GrowArrow(v_arr),
            m.GrowArrow(w_arr),
            m.Write(v_label),
            m.Write(w_label),
        )
        self.wait(0.5)

        para = m.Polygon(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(V[0], V[1]),
            plane.coords_to_point((V + W)[0], (V + W)[1]),
            plane.coords_to_point(W[0], W[1]),
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.3,
            stroke_width=2,
        )
        self.play(m.FadeIn(para))

        cross_val = V[0] * W[1] - V[1] * W[0]
        cross = (
            m.MathTex(
                "\\vec{v} \\times \\vec{w} = v_x w_y - v_y w_x = ",
                f"{cross_val:g}",
            )
            .scale(0.85)
            .to_edge(m.DOWN, buff=0.5)
        )
        cross[1].set_color(m.BLUE)
        self.play(m.Write(cross))

        area_label = m.MathTex(
            f"\\text{{Area}} = {abs(cross_val):g}",
            color=m.BLUE,
        ).to_corner(m.UR, buff=0.5)
        bg = m.BackgroundRectangle(
            area_label, color=m.BLACK, fill_opacity=0.75, buff=0.12
        )
        self.play(m.FadeIn(bg), m.Write(area_label))
        self.wait(2.0)
