# Source: manim/mobject/text/text_mobject.py
import manimgx as m


class PangoRender(m.Scene):
    def construct(self):
        morning = m.Text("வணக்கம்", font="sans-serif")
        self.play(m.Write(morning))
        self.wait(2)
