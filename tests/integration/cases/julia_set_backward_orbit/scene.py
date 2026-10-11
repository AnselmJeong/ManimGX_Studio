import cmath
import math
import random

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        random.seed(3)
        title = m.Tex("Julia set: backward orbit of $f(z)=z^2+c$").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        plane = (
            m.NumberPlane(
                x_range=[-2, 2, 1],
                y_range=[-2, 2, 1],
                background_line_style={
                    "stroke_opacity": 0.25,
                    "stroke_color": m.GREY_B,
                },
            )
            .scale(0.85)
            .shift(m.DOWN * 0.3)
        )
        self.play(m.Create(plane))

        c = -0.7 + 0.27j
        orbits: list[complex] = []
        z = 0.5 + 0.5j
        for _ in range(2500):
            w = z - c
            r = abs(w)
            theta = cmath.phase(w)
            sign = random.choice([1, -1])
            z = math.sqrt(r) * cmath.exp(
                1j * (theta / 2 + (math.pi if sign < 0 else 0))
            )
            orbits.append(z)

        dots = m.VGroup()
        for zz in orbits[200:]:
            if abs(zz.real) < 2 and abs(zz.imag) < 2:
                dots.add(
                    m.Dot(
                        plane.coords_to_point(zz.real, zz.imag),
                        color=m.YELLOW,
                        radius=0.018,
                    )
                )

        self.play(m.FadeIn(dots), run_time=2.5)

        c_lab = (
            m.MathTex("c = -0.7 + 0.27i", color=m.RED)
            .scale(0.8)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(c_lab))
        self.wait(1.5)
