# Source: manim/utils/debug.py
import manimgx as m


class IndexLabelsExample(m.Scene):
    def construct(self):
        text = m.MathTex(
            "\\frac{d}{dx}f(x)g(x)=",
            "f(x)\\frac{d}{dx}g(x)",
            "+",
            "g(x)\\frac{d}{dx}f(x)",
        )

        # index the fist term in the MathTex mob
        indices = m.index_labels(text[0])

        text[0][1].set_color(m.PURPLE_B)
        text[0][8:12].set_color(m.DARK_BLUE)

        self.add(text, indices)
