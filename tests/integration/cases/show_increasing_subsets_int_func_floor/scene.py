# Source: manim/animation/creation.py
import numpy as np

import manimgx as m


class ShowIncreasingSubsetsIntFuncFloor(m.Scene):
    def construct(self):
        p = m.VGroup(m.Dot(), m.Square(), m.Triangle())
        self.add(p)
        self.play(m.ShowIncreasingSubsets(p, int_func=np.floor))
        self.wait(0.2)
