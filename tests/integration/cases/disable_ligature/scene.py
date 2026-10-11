# Source: docs/source/guides/using_text.rst
import manimgx as m


class DisableLigature(m.Scene):
    def construct(self):
        li = m.Text("fl ligature", font_size=96)
        nli = m.Text("fl ligature", disable_ligatures=True, font_size=96)
        self.add(m.Group(li, nli).arrange(m.DOWN, buff=0.8))
        self.wait()
