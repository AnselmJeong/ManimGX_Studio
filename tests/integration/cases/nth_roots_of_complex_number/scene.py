import math

import manimgx as m

N = 5
W_REAL = 1.0
W_IMAG = 0.0


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-2, 2, 1],
            y_range=[-2, 2, 1],
            x_length=8,
            y_length=8,
        )
        self.play(m.Create(plane), run_time=1.0)

        w_mag = math.hypot(W_REAL, W_IMAG)
        w_arg = math.atan2(W_IMAG, W_REAL)
        radius = w_mag ** (1.0 / N)

        origin = plane.coords_to_point(0.0, 0.0)
        circle_radius_world = plane.coords_to_point(radius, 0.0)[0] - origin[0]
        circle = m.Circle(
            radius=circle_radius_world,
            color=m.WHITE,
            stroke_width=2,
        ).move_to(origin)
        self.play(m.Create(circle))

        root_points = [
            plane.coords_to_point(
                radius * math.cos((w_arg + 2 * math.pi * k) / N),
                radius * math.sin((w_arg + 2 * math.pi * k) / N),
            )
            for k in range(N)
        ]
        dots = m.VGroup(*[m.Dot(p, color=m.YELLOW, radius=0.11) for p in root_points])
        self.play(
            m.LaggedStart(*[m.FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.1),
            run_time=1.2,
        )

        polygon = m.Polygon(
            *root_points,
            color=m.BLUE,
            stroke_width=2,
            fill_opacity=0.0,
        )
        self.play(m.Create(polygon), run_time=1.4)

        title = (
            m.MathTex(
                f"z^{{{N}}}",
                "=",
                "1",
            )
            .scale(1.5)
            .to_edge(m.UP)
        )
        title[0].set_color(m.YELLOW)
        sub = (
            m.Tex(
                f"{N} roots of unity",
            )
            .scale(0.7)
            .next_to(title, m.DOWN, buff=0.2)
        )
        self.play(m.Write(title), m.Write(sub))
        self.wait(2.0)
