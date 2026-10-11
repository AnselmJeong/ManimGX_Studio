# Source: manim/mobject/svg/brace.py
import manimgx as m


class BraceTextExample(m.Scene):
    def construct(self):
        s1 = m.Square().move_to(2 * m.LEFT)
        self.add(s1)
        br1 = m.BraceText(s1, "Label")
        self.add(br1)

        s2 = m.Square().move_to(2 * m.RIGHT)
        self.add(s2)
        br2 = m.BraceText(s2, "Label")

        br2.change_label("new")
        self.add(br2)
        self.wait(0.1)
