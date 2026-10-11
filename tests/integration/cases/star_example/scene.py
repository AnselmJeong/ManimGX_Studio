# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class StarExample(m.Scene):
    def construct(self):
        pentagram = m.RegularPolygram(5, radius=2)
        star = m.Star(outer_radius=2, color=m.RED)

        self.add(pentagram)
        self.play(m.Create(star), run_time=3)
        self.play(m.FadeOut(star), run_time=2)
