# Source: docs/source/guides/using_text.rst
import manimgx as m


class SlantsExample(m.Scene):
    def construct(self):
        a = m.Text("Italic", slant=m.ITALIC)
        self.add(a)
        self.wait()
