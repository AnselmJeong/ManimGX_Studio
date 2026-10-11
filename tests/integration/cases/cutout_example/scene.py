# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class CutoutExample(m.Scene):
    def construct(self):
        s1 = m.Square().scale(2.5)
        s2 = m.Triangle().shift(m.DOWN + m.RIGHT).scale(0.5)
        s3 = m.Square().shift(m.UP + m.RIGHT).scale(0.5)
        s4 = m.RegularPolygon(5).shift(m.DOWN + m.LEFT).scale(0.5)
        s5 = m.RegularPolygon(6).shift(m.UP + m.LEFT).scale(0.5)
        c = m.Cutout(
            s1, s2, s3, s4, s5, fill_opacity=1, color=m.BLUE, stroke_color=m.RED
        )
        self.play(m.Write(c), run_time=4)
        self.wait()
