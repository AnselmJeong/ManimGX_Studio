import math

import numpy as np

import manimgx as m

V = np.array([3.0, 2.0])
LINE_ANGLE = math.pi / 6


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
        v_end = plane.coords_to_point(V[0], V[1])
        v_arrow = m.Arrow(origin, v_end, color=m.YELLOW, buff=0, stroke_width=5)
        v_label = m.MathTex("\\vec{v}", color=m.YELLOW).next_to(
            v_arrow.get_end(), m.UP, buff=0.15
        )
        self.play(m.GrowArrow(v_arrow), m.Write(v_label))
        self.wait(0.4)

        line_dir = np.array([math.cos(LINE_ANGLE), math.sin(LINE_ANGLE)])
        line_start = plane.coords_to_point(*(-1.0 * line_dir))
        line_end = plane.coords_to_point(*(5.0 * line_dir))
        line = m.Line(line_start, line_end, color=m.BLUE, stroke_width=2.5)
        line_label = (
            m.Tex("target line")
            .scale(0.6)
            .set_color(m.BLUE)
            .next_to(
                line.get_end(),
                m.UR,
                buff=0.1,
            )
        )
        self.play(m.Create(line), m.Write(line_label))
        self.wait(0.4)

        proj_scalar = float(np.dot(V, line_dir))
        proj_xy = proj_scalar * line_dir
        proj_pt = plane.coords_to_point(proj_xy[0], proj_xy[1])

        perpendicular = m.DashedLine(v_end, proj_pt, color=m.GREY, stroke_width=2.5)
        proj_arrow = m.Arrow(origin, proj_pt, color=m.GREEN, buff=0, stroke_width=5)

        self.play(m.Create(perpendicular))
        self.play(m.GrowArrow(proj_arrow))

        proj_label = m.MathTex(
            f"\\vec{{v}} \\cdot \\hat{{u}} = {proj_scalar:.2f}",
            color=m.GREEN,
        ).to_corner(m.UR, buff=0.5)
        bg = m.BackgroundRectangle(
            proj_label, color=m.BLACK, fill_opacity=0.78, buff=0.12
        )
        self.play(m.FadeIn(bg), m.Write(proj_label))
        self.wait(2.0)
