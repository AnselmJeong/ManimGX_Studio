# Source: manim/mobject/text/text_mobject.py
import manimgx as m


class ParagraphTwoLinesExample(m.Scene):
    def construct(self):
        para = m.Paragraph("Hello", "World", font_size=72)
        self.play(m.FadeIn(para))
        self.wait(0.2)
