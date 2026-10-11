# Source: manim/animation/indication.py
import manimgx as m


class UsingCircumscribe(m.Scene):
    def construct(self):
        lbl = m.Tex(r"Circum-\\scribe").scale(2)
        self.add(lbl)
        self.play(m.Circumscribe(lbl))
        self.play(m.Circumscribe(lbl, m.Circle))
        self.play(m.Circumscribe(lbl, fade_out=True))
        self.play(m.Circumscribe(lbl, time_width=2))
        self.play(m.Circumscribe(lbl, m.Circle, True))
