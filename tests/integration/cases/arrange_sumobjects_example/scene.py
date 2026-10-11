# Source: manim/mobject/mobject.py
import numpy as np

import manimgx as m


class ArrangeSumobjectsExample(m.Scene):
    def construct(self):
        np.random.seed(0)
        s = m.VGroup(
            *[
                m.Dot().shift(
                    i * 0.1 * m.RIGHT * np.random.uniform(-1, 1)
                    + m.UP * np.random.uniform(-1, 1)
                )
                for i in range(15)
            ]
        )
        s.shift(m.UP).set_color(m.BLUE)
        s2 = s.copy().set_color(m.RED)
        s2.arrange_submobjects()
        s2.shift(m.DOWN)
        self.add(s, s2)
        self.wait()
