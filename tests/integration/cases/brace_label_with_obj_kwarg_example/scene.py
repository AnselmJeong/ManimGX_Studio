# Source: manim/mobject/svg/brace.py
import manimgx as m


class BraceLabelWithObjKwargExample(m.Scene):
    def construct(self):
        square = m.Square(side_length=2.0)
        brace = m.BraceLabel(obj=square, text="L")
        self.play(m.FadeIn(square), m.FadeIn(brace))
        self.wait(0.2)
