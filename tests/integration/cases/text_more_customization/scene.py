# Source: manim/mobject/text/text_mobject.py
import manimgx as m


class TextMoreCustomization(m.Scene):
    def construct(self):
        text1 = m.Text(
            "Google",
            t2c={
                "[:1]": "#3174f0",
                "[1:2]": "#e53125",
                "[2:3]": "#fbb003",
                "[3:4]": "#3174f0",
                "[4:5]": "#269a43",
                "[5:]": "#e53125",
            },
            font_size=58,
        ).scale(3)
        self.add(text1)
        self.wait()
