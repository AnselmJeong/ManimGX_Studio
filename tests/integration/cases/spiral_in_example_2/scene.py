# Source: example_scenes/basic.py
import numpy as np

import manimgx as m


class SpiralInExample(m.Scene):
    def construct(self):
        logo_green = "#81b29a"
        logo_blue = "#454866"
        logo_red = "#e07a5f"

        font_color = "#ece6e2"

        pi = m.MathTex(r"\pi").scale(7).set_color(font_color)
        pi.shift(2.25 * m.LEFT + 1.5 * m.UP)

        circle = m.Circle(color=logo_green, fill_opacity=0.7, stroke_width=0).shift(
            m.LEFT
        )
        square = m.Square(color=logo_blue, fill_opacity=0.8, stroke_width=0).shift(m.UP)
        triangle = m.Triangle(color=logo_red, fill_opacity=0.9, stroke_width=0).shift(
            m.RIGHT
        )
        pentagon = m.Polygon(
            *[
                [
                    np.cos(2 * np.pi / 5 * i),
                    np.sin(2 * np.pi / 5 * i),
                    0,
                ]
                for i in range(5)
            ],
            color=m.PURPLE_B,
            fill_opacity=1,
            stroke_width=0,
        ).shift(m.UP + 2 * m.RIGHT)
        shapes = m.VGroup(triangle, square, circle, pentagon, pi)
        self.play(m.SpiralIn(shapes, fade_in_fraction=0.9))
        self.wait()
        self.play(m.FadeOut(shapes))
