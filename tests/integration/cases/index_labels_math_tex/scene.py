# Source: docs/source/guides/using_text.rst
import manimgx as m


class IndexLabelsMathTex(m.Scene):
    def construct(self):
        text = m.MathTex(r"\binom{2n}{n+2}", font_size=96)

        # index the first (and only) term of the MathTex mob
        self.add(m.index_labels(text[0]))

        text[0][1:3].set_color(m.YELLOW)
        text[0][3:6].set_color(m.RED)
        self.add(text)
