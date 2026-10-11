# Source: docs/source/guides/using_text.rst
import manimgx as m


class GradientExample(m.Scene):
    def construct(self):
        t = m.Text("Hello", gradient=(m.RED, m.BLUE, m.GREEN), font_size=96)
        self.add(t)
        self.wait()
