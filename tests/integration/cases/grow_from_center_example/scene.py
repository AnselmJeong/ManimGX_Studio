# Source: manim/animation/growing.py
import manimgx as m


class GrowFromCenterExample(m.Scene):
    def construct(self):
        squares = [m.Square() for _ in range(2)]
        m.VGroup(*squares).set_x(0).arrange(buff=2)
        self.play(m.GrowFromCenter(squares[0]))
        self.play(m.GrowFromCenter(squares[1], point_color=m.RED))
