# Source: manim/mobject/mobject.py
import manimgx as m


class WidthExample(m.Scene):
    def construct(self):
        decimal = m.DecimalNumber().to_edge(m.UP)
        rect = m.Rectangle(color=m.BLUE)
        rect_copy = rect.copy().set_stroke(m.GRAY, opacity=0.5)

        decimal.add_updater(lambda d: d.set_value(rect.width))

        self.add(rect_copy, rect, decimal)
        self.play(rect.animate.set(width=7))
        self.wait()
