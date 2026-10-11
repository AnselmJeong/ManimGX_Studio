# Source: manim/mobject/geometry/line.py
import manimgx as m


class ElbowExample(m.Scene):
    def construct(self):
        elbow_1 = m.Elbow()
        elbow_2 = m.Elbow(width=2.0)
        elbow_3 = m.Elbow(width=2.0, angle=5 * m.PI / 4)

        elbow_group = m.Group(elbow_1, elbow_2, elbow_3).arrange(buff=1)
        self.add(elbow_group)
        self.wait()
