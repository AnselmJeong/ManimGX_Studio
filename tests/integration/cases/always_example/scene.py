# Source: manim/mobject/mobject.py
import manimgx as m


class AlwaysExample(m.Scene):
    def construct(self):
        sq = m.Square().to_edge(m.LEFT)
        t = m.Text("Hello World!")
        t.always.next_to(sq, m.UP)
        self.add(sq, t)
        self.play(sq.animate.to_edge(m.RIGHT))
