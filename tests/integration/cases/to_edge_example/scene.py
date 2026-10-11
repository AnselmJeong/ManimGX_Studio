# Source: manim/mobject/mobject.py
import manimgx as m


class ToEdgeExample(m.Scene):
    def construct(self):
        tex_top = m.Tex("I am at the top!")
        tex_top.to_edge(m.UP)
        tex_side = m.Tex("I am moving to the side!")
        c = m.Circle().shift(2 * m.DOWN)
        self.add(tex_top, tex_side, c)
        tex_side.to_edge(m.LEFT)
        c.to_edge(m.RIGHT, buff=0)
        self.wait()
