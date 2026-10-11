# Source: manim/mobject/table.py
import manimgx as m


class BackgroundRectanglesExample(m.Scene):
    def construct(self):
        background = m.Rectangle(height=6.5, width=13)
        background.set_fill(opacity=0.5)
        background.set_color(m.TEAL)
        self.add(background)
        t0 = m.Table(
            [["This", "is a"], ["simple", "Table."]],
            add_background_rectangles_to_entries=True,
        )
        t1 = m.Table(
            [["This", "is a"], ["simple", "Table."]], include_background_rectangle=True
        )
        g = m.Group(t0, t1).scale(0.7).arrange(buff=0.5)
        self.add(g)
        self.wait()
