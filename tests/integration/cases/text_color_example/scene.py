# Source: manim/mobject/text/text_mobject.py
import manimgx as m


class TextColorExample(m.Scene):
    def construct(self):
        text1 = m.Text("Hello world", color=m.BLUE).scale(3)
        text2 = (
            m.Text("Hello world", gradient=(m.BLUE, m.GREEN))
            .scale(3)
            .next_to(text1, m.DOWN)
        )
        self.add(text1, text2)
        self.wait()
