# Source: manim/mobject/text/numbers.py
import manimgx as m


class IntegerExample(m.Scene):
    def construct(self):
        self.add(
            m.Integer(number=2.5).set_color(m.ORANGE).scale(2.5).set_x(-0.5).set_y(0.8)
        )
        self.add(
            m.Integer(number=3.14159, show_ellipsis=True)
            .set_x(3)
            .set_y(3.3)
            .scale(3.14159)
        )
        self.add(
            m.Integer(number=42)
            .set_x(2.5)
            .set_y(-2.3)
            .set_color_by_gradient(m.BLUE, m.TEAL)
            .scale(1.7)
        )
        self.add(
            m.Integer(number=6.28).set_x(-1.5).set_y(-2).set_color(m.YELLOW).scale(1.4)
        )
        self.wait()
