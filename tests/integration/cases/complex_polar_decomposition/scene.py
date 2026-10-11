import math

import numpy as np

import manimgx as m

REAL = 1.0
IMAG = math.sqrt(3.0)


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-3, 3, 1],
            y_range=[-2, 3, 1],
            x_length=10,
            y_length=8,
        )
        self.play(m.Create(plane), run_time=1.0)

        origin = plane.coords_to_point(0.0, 0.0)
        point = plane.coords_to_point(REAL, IMAG)
        x_proj = plane.coords_to_point(REAL, 0.0)

        dot = m.Dot(point, color=m.YELLOW, radius=0.1)
        label = m.MathTex("z = 1 + i\\sqrt{3}", color=m.YELLOW).next_to(
            dot,
            m.UR,
            buff=0.15,
        )
        self.play(m.FadeIn(dot, scale=0.4), m.Write(label))

        x_line = m.Line(origin, x_proj, color=m.BLUE, stroke_width=5)
        y_line = m.Line(x_proj, point, color=m.GOLD, stroke_width=5)
        z_line = m.Line(origin, point, color=m.WHITE, stroke_width=4)
        x_label = m.MathTex("1", color=m.BLUE).next_to(x_line, m.DOWN, buff=0.15)
        y_label = m.MathTex("\\sqrt{3}", color=m.GOLD).next_to(
            y_line, m.RIGHT, buff=0.15
        )

        self.play(m.Create(x_line), m.Write(x_label))
        self.play(m.Create(y_line), m.Write(y_label))
        self.play(m.Create(z_line))
        self.wait(0.3)

        unit = (point - origin) / np.linalg.norm(point - origin)
        normal = np.array([-unit[1], unit[0], 0.0])
        mag_label = m.MathTex("|z| = 2", color=m.WHITE).scale(0.9)
        midpoint = (origin + point) / 2
        mag_label.move_to(midpoint + 0.4 * normal)
        self.play(m.Write(mag_label))

        angle_arc = m.Arc(
            radius=0.7,
            start_angle=0,
            angle=math.pi / 3,
            color=m.RED,
            stroke_width=3,
        )
        angle_arc.shift(origin)
        angle_label = m.MathTex("\\theta = \\tfrac{\\pi}{3}", color=m.RED).scale(0.85)
        angle_label.move_to(
            origin
            + 1.15 * np.array([math.cos(math.pi / 6), math.sin(math.pi / 6), 0.0])
        )
        self.play(m.Create(angle_arc), m.Write(angle_label))
        self.wait(2.0)
