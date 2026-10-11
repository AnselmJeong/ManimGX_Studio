# Source: docs/source/guides/using_text.rst
import manimgx as m


class SimpleColor(m.Scene):
    def construct(self):
        col = m.Text("RED COLOR", color=m.RED)
        self.add(col)
        self.wait()
