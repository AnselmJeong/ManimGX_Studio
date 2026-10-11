# Source: manim/mobject/geometry/shape_matchers.py
import manimgx as m


class BackgroundRectangleStrokeOpacityKwarg(m.Scene):
    def construct(self):
        target = m.Text("hello", color=m.YELLOW).scale(1.2)
        # CE accepts stroke_opacity on BackgroundRectangle — verify the kwarg.
        bg = m.BackgroundRectangle(
            target,
            color=m.WHITE,
            buff=0.3,
            fill_opacity=0.4,
            stroke_opacity=0.0,
        )
        self.add(bg, target)
        self.wait()
