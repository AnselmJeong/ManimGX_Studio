# Source: manim/mobject/geometry/shape_matchers.py
import manimgx as m


class ExampleBackgroundRectangle(m.Scene):
    def construct(self):
        circle = m.Circle().shift(m.LEFT)
        circle.set_stroke(color=m.GREEN, width=20)
        triangle = m.Triangle().shift(2 * m.RIGHT)
        triangle.set_fill(m.PINK, opacity=0.5)
        backgroundRectangle1 = m.BackgroundRectangle(
            circle, color=m.WHITE, fill_opacity=0.15
        )
        backgroundRectangle2 = m.BackgroundRectangle(
            triangle, color=m.WHITE, fill_opacity=0.15
        )
        self.add(backgroundRectangle1)
        self.add(backgroundRectangle2)
        self.add(circle)
        self.add(triangle)
        self.play(m.Rotate(backgroundRectangle1, m.PI / 4))
        self.play(m.Rotate(backgroundRectangle2, m.PI / 2))
