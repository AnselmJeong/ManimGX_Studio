# Source: manim/mobject/matrix.py
import manimgx as m


class BackgroundRectanglesExample(m.Scene):
    def construct(self):
        background = m.Rectangle().scale(3.2)
        background.set_fill(opacity=0.5)
        background.set_color(m.TEAL)
        self.add(background)
        m0 = m.Matrix([[12, -30], [-1, 15]], add_background_rectangles_to_entries=True)
        m1 = m.Matrix([[2, 0], [-1, 1]], include_background_rectangle=True)
        m2 = m.Matrix([[12, -30], [-1, 15]])
        g = m.Group(m0, m1, m2).arrange(buff=2)
        self.add(g)
        self.wait()
