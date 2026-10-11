# Source: manim/mobject/opengl/opengl_vectorized_mobject.py
import manimgx as m


class ChangeOfDirection(m.Scene):
    def construct(self):
        ccw = m.RegularPolygon(5)
        ccw.shift(m.LEFT)
        cw = m.RegularPolygon(5)
        cw.shift(m.RIGHT).reverse_direction()

        self.play(m.Create(ccw), m.Create(cw), run_time=4)
