# Source: docs/source/guides/using_text.rst
import manimgx as m


class HelloWorld(m.Scene):
    def construct(self):
        text = m.Text("Hello world", font_size=144)
        self.add(text)
        self.wait()
