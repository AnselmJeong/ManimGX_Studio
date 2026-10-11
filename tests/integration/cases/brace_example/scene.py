# Source: manim/mobject/svg/brace.py
import numpy as np

import manimgx as m


class BraceExample(m.Scene):
    def construct(self):
        s = m.Square()
        self.add(s)
        for i in np.linspace(0.1, 1.0, 4):
            br = m.Brace(s, sharpness=i)
            t = m.Text(f"sharpness= {i}").next_to(br, m.RIGHT)
            self.add(t)
            self.add(br)
        m.VGroup(*self.mobjects).arrange(m.DOWN, buff=0.2)
        self.wait()
