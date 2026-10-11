# Source: manim/mobject/geometry/arc.py
import manimgx as m


class SeveralLabeledDots(m.Scene):
    def construct(self):
        sq = m.Square(fill_color=m.RED, fill_opacity=1)
        self.add(sq)
        dot1 = m.LabeledDot(m.Tex("42", color=m.RED))
        dot2 = m.LabeledDot(m.MathTex("a", color=m.GREEN))
        dot3 = m.LabeledDot(m.Text("ii", color=m.BLUE))
        dot4 = m.LabeledDot("3")
        dot1.next_to(sq, m.UL)
        dot2.next_to(sq, m.UR)
        dot3.next_to(sq, m.DL)
        dot4.next_to(sq, m.DR)
        self.add(dot1, dot2, dot3, dot4)
        self.wait()
