# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class SquareExample(m.Scene):
    def construct(self):
        square_1 = m.Square(side_length=2.0).shift(m.DOWN)
        square_2 = m.Square(side_length=1.0).next_to(square_1, direction=m.UP)
        square_3 = m.Square(side_length=0.5).next_to(square_2, direction=m.UP)
        self.add(square_1, square_2, square_3)
        self.wait()
