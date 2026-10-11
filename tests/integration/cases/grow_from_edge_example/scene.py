# Source: manim/animation/growing.py
import manimgx as m


class GrowFromEdgeExample(m.Scene):
    def construct(self):
        squares = [m.Square() for _ in range(4)]
        m.VGroup(*squares).set_x(0).arrange(buff=1)
        self.play(m.GrowFromEdge(squares[0], m.DOWN))
        self.play(m.GrowFromEdge(squares[1], m.RIGHT))
        self.play(m.GrowFromEdge(squares[2], m.UR))
        self.play(m.GrowFromEdge(squares[3], m.UP, point_color=m.RED))
