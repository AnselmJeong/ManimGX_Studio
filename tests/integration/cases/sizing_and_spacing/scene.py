# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class SizingAndSpacing(m.Scene):
    def construct(self):
        def func(pos):
            return np.sin(pos[0] / 2) * m.UR + np.cos(pos[1] / 2) * m.LEFT

        vf = m.ArrowVectorField(func, x_range=[-7, 7, 1])
        self.add(vf)
        self.wait()

        length_func = lambda x: x / 3
        vf2 = m.ArrowVectorField(func, x_range=[-7, 7, 1], length_func=length_func)
        self.play(vf.animate.become(vf2))
        self.wait()
