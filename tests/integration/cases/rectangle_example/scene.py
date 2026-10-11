# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class RectangleExample(m.Scene):
    def construct(self):
        rect1 = m.Rectangle(width=4.0, height=2.0, grid_xstep=1.0, grid_ystep=0.5)
        rect2 = m.Rectangle(width=1.0, height=4.0)
        rect3 = m.Rectangle(width=2.0, height=2.0, grid_xstep=1.0, grid_ystep=1.0)
        rect3.grid_lines.set_stroke(width=1)

        rects = m.Group(rect1, rect2, rect3).arrange(buff=1)
        self.add(rects)
        self.wait()
