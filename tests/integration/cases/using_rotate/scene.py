# Source: manim/animation/rotation.py
import manimgx as m


class UsingRotate(m.Scene):
    def construct(self):
        self.play(
            m.Rotate(
                m.Square(side_length=0.5).shift(m.UP * 2),
                angle=2 * m.PI,
                about_point=m.ORIGIN,
                rate_func=m.linear,
            ),
            m.Rotate(m.Square(side_length=0.5), angle=2 * m.PI, rate_func=m.linear),
        )
