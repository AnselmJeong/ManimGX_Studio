# Source: docs/source/guides/using_text.rst
import manimgx as m


class LineSpacing(m.Scene):
    def construct(self):
        a = m.Text("Hello\nWorld", line_spacing=1)
        b = m.Text("Hello\nWorld", line_spacing=4)
        self.add(m.Group(a, b).arrange(m.LEFT, buff=5))
        self.wait()
