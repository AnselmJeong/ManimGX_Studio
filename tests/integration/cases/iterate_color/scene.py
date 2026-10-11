# Source: docs/source/guides/using_text.rst
import manimgx as m


class IterateColor(m.Scene):
    def construct(self):
        text = m.Text("Colors", font_size=96)
        for letter in text:
            letter.set_color(m.random_bright_color())
        self.add(text)
