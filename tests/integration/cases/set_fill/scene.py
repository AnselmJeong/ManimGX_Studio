# Source: manim/mobject/opengl/opengl_vectorized_mobject.py
import manimgx as m


class SetFill(m.Scene):
    def construct(self):
        square = m.Square().scale(2).set_fill(m.WHITE, 1)
        circle1 = m.Circle().set_fill(m.GREEN, 0.8)
        circle2 = m.Circle().set_fill(m.YELLOW)  # No fill_opacity
        circle3 = m.Circle().set_fill(color="#FF2135", opacity=0.2)
        group = m.Group(circle1, circle2, circle3).arrange()
        self.add(square)
        self.add(group)
        self.wait()
