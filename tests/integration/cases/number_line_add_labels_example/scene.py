# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class NumberLineAddLabelsExample(m.Scene):
    def construct(self):
        nl = m.NumberLine(x_range=(-3, 3, 1))
        nl.add_labels({-2: "a", 0: "b", 2: "c"})
        self.add(nl, nl.labels)
        self.wait()
