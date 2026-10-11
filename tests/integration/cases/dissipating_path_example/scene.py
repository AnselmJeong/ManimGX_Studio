# Source: manim/animation/changing.py
import manimgx as m


class DissipatingPathExample(m.Scene):
    def construct(self):
        a = m.Dot(m.RIGHT * 2)
        b = m.TracedPath(a.get_center, dissipating_time=0.5, stroke_opacity=[0, 1])
        self.add(a, b)
        self.play(a.animate(path_arc=m.PI / 4).shift(m.LEFT * 2))
        self.play(a.animate(path_arc=-m.PI / 4).shift(m.LEFT * 2))
        self.wait()
