# Source: manim/mobject/mobject.py
import numpy as np

import manimgx as m


class ApplyFuncExample(m.Scene):
    def construct(self):
        circ = m.Circle().scale(1.5)
        circ_ref = circ.copy()
        circ.apply_complex_function(lambda x: np.exp(x * 1j))
        t = m.ValueTracker(0)
        circ.add_updater(
            lambda x: x.become(
                circ_ref.copy().apply_complex_function(
                    lambda x: np.exp(x + t.get_value() * 1j)
                )
            ).set_color(m.BLUE)
        )
        self.add(circ_ref)
        self.play(m.TransformFromCopy(circ_ref, circ))
        self.play(t.animate.set_value(m.TAU), run_time=3)
