# Source: manim/animation/transform.py
import manimgx as m


class CyclicReplaceExample(m.Scene):
    def construct(self):
        group = m.VGroup(m.Square(), m.Circle(), m.Triangle(), m.Star())
        group.arrange(m.RIGHT)
        self.add(group)

        for _ in range(4):
            self.play(m.CyclicReplace(*group))
