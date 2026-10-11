# Source: manim/mobject/mobject.py
import manimgx as m


class AngleMidPoint(m.Scene):
    def construct(self):
        line1 = m.Line(m.ORIGIN, 2 * m.RIGHT)
        line2 = m.Line(m.ORIGIN, 2 * m.RIGHT).rotate_about_origin(80 * m.DEGREES)

        a = m.Angle(line1, line2, radius=1.5, other_angle=False)
        d = m.Dot(a.get_midpoint()).set_color(m.RED)

        self.add(line1, line2, a, d)
        self.wait()
