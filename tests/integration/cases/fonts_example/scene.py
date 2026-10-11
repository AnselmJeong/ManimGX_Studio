# Source: docs/source/guides/using_text.rst
import manimgx as m


class FontsExample(m.Scene):
    def construct(self):
        ft = m.Text("Noto Sans", font="Noto Sans")
        self.add(ft)
