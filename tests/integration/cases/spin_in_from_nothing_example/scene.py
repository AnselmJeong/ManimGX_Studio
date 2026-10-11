# Source: manim/animation/growing.py
import manimgx as m


class SpinInFromNothingExample(m.Scene):
    def construct(self):
        squares = [m.Square() for _ in range(3)]
        m.VGroup(*squares).set_x(0).arrange(buff=2)
        self.play(m.SpinInFromNothing(squares[0]))
        self.play(m.SpinInFromNothing(squares[1], angle=2 * m.PI))
        self.play(m.SpinInFromNothing(squares[2], point_color=m.RED))
