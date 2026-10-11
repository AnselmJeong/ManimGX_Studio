# Source: manim/mobject/mobject.py
import manimgx as m


class RotateMethodExample(m.Scene):
    def construct(self):
        circle = m.Circle(radius=1, color=m.BLUE)
        line = m.Line(start=m.ORIGIN, end=m.RIGHT)
        arrow1 = m.Arrow(start=m.ORIGIN, end=m.RIGHT, buff=0, color=m.GOLD)
        group1 = m.VGroup(circle, line, arrow1)

        group2 = group1.copy()
        arrow2 = group2[2]
        assert isinstance(arrow2, m.Arrow)
        arrow2.rotate(angle=m.PI / 4, about_point=arrow2.get_start())

        group3 = group1.copy()
        arrow3 = group3[2]
        assert isinstance(arrow3, m.Arrow)
        arrow3.rotate(angle=120 * m.DEGREES, about_point=arrow3.get_start())

        self.add(m.VGroup(group1, group2, group3).arrange(m.RIGHT, buff=1))
        self.wait()
