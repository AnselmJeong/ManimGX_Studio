# Source: manim/mobject/svg/brace.py
import manimgx as m


class ArcBraceExample(m.Scene):
    def construct(self):
        arc_1 = m.Arc(radius=1.5, start_angle=0, angle=2 * m.PI / 3).set_color(m.RED)
        brace_1 = m.ArcBrace(arc_1, m.LEFT)
        group_1 = m.VGroup(arc_1, brace_1)

        arc_2 = m.Arc(radius=3, start_angle=0, angle=5 * m.PI / 6).set_color(m.YELLOW)
        brace_2 = m.ArcBrace(arc_2)
        group_2 = m.VGroup(arc_2, brace_2)

        arc_3 = m.Arc(radius=0.5, start_angle=-0, angle=m.PI).set_color(m.BLUE)
        brace_3 = m.ArcBrace(arc_3)
        group_3 = m.VGroup(arc_3, brace_3)

        arc_4 = m.Arc(radius=0.2, start_angle=0, angle=3 * m.PI / 2).set_color(m.GREEN)
        brace_4 = m.ArcBrace(arc_4)
        group_4 = m.VGroup(arc_4, brace_4)

        arc_group = m.VGroup(group_1, group_2, group_3, group_4).arrange_in_grid(
            buff=1.5
        )
        self.add(arc_group.move_to(m.ORIGIN))
