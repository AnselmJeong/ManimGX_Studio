# Source: manim/mobject/geometry/labeled.py
import manimgx as m


class LabeledArrowExample(m.Scene):
    def construct(self):
        l_arrow = m.LabeledArrow(
            "0.5", start=m.LEFT * 3, end=m.RIGHT * 3 + m.UP * 2, label_position=0.5
        )

        self.add(l_arrow)
        self.wait()
