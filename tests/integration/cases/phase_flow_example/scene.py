# Source: manim/animation/movement.py
import numpy as np

import manimgx as m


class PhaseFlowExample(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)

        def field(p):
            return np.array([0.5, 0.0, 0.0])

        self.play(m.PhaseFlow(field, square, virtual_time=1.5, run_time=1.0))
