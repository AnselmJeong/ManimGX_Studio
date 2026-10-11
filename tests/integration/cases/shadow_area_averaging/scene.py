import math
import random

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        random.seed(0)
        title = m.Tex("Average shadow of a cube").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        axes = m.Axes(
            x_range=[0, 50, 10],
            y_range=[0, 3, 1],
            x_length=8.0,
            y_length=3.0,
            tips=False,
            axis_config={"include_numbers": True, "stroke_width": 1.5},
        ).shift(m.DOWN * 0.5)
        x_lab = (
            m.Tex("samples", color=m.WHITE).scale(0.6).next_to(axes, m.DOWN, buff=0.2)
        )
        y_lab = (
            m.Tex("avg area", color=m.WHITE).scale(0.6).next_to(axes, m.UP, buff=0.2)
        )
        self.play(m.Create(axes), m.Write(x_lab), m.Write(y_lab))

        target = 1.5
        line = axes.plot(lambda x: target, color=m.YELLOW, x_range=[0, 50])
        t_lab = (
            m.MathTex("\\langle A\\rangle = \\tfrac{3}{2}", color=m.YELLOW)
            .scale(0.7)
            .next_to(line, m.RIGHT, buff=0.2)
        )
        self.play(m.Create(line), m.Write(t_lab))

        points = []
        total = 0.0
        for i in range(1, 51):
            sample = target + random.gauss(0, 0.45) / math.sqrt(i / 6 + 1)
            total += sample
            avg = total / i
            points.append(axes.coords_to_point(i, max(0.0, min(3.0, avg))))
        path = m.VMobject(stroke_color=m.GREEN, stroke_width=3.0)
        path.set_points_as_corners(points)
        self.play(m.Create(path), run_time=3.0)
        self.wait(1.5)
