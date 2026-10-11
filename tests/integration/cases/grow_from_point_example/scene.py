# Source: manim/animation/growing.py
import manimgx as m


class GrowFromPointExample(m.Scene):
    def construct(self):
        dot = m.Dot(3 * m.UR, color=m.GREEN)
        squares = [m.Square() for _ in range(4)]
        m.VGroup(*squares).set_x(0).arrange(buff=1)
        self.add(dot)
        self.play(m.GrowFromPoint(squares[0], m.ORIGIN))
        self.play(m.GrowFromPoint(squares[1], [-2, 2, 0]))
        self.play(m.GrowFromPoint(squares[2], [3, -2, 0], m.RED))
        self.play(m.GrowFromPoint(squares[3], dot, dot.get_color()))
