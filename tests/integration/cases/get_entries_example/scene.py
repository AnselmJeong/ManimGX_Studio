# Source: manim/mobject/matrix.py
import manimgx as m


class GetEntriesExample(m.Scene):
    def construct(self):
        m0 = m.Matrix([[2, 3], [1, 5]])
        ent = m0.get_entries()
        colors = [m.BLUE, m.GREEN, m.YELLOW, m.RED]
        for k in range(len(colors)):
            ent[k].set_color(colors[k])
        self.add(m0)
        self.wait()
