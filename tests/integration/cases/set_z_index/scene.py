# Source: manim/mobject/mobject.py
import manimgx as m


class SetZIndex(m.Scene):
    def construct(self):
        text = m.Text("z_index = 3", color=m.PURE_RED).shift(m.UP).set_z_index(3)
        square = m.Square(2, fill_opacity=1).set_z_index(2)
        tex = m.Tex(r"zIndex = 1", color=m.PURE_BLUE).shift(m.DOWN).set_z_index(1)
        circle = m.Circle(radius=1.7, color=m.GREEN, fill_opacity=1)  # z_index = 0

        # Displaying order is now defined by z_index values
        self.add(text)
        self.add(square)
        self.add(tex)
        self.add(circle)
        self.wait()
