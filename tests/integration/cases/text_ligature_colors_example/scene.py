# Source: manimgx API coverage (CE 0.21 `Text t2c across ligatures`)
import manimgx as m


class TextLigatureColorsExample(m.Scene):
    def construct(self):
        text = m.Text("office fish", t2c={"f": m.RED, "i": m.BLUE}, font_size=96)
        self.play(m.FadeIn(text))
