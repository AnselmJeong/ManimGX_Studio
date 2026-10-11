# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class ScaleVectorFieldFunction(m.Scene):
    def construct(self):
        def func(pos):
            return np.sin(pos[1]) * m.RIGHT + np.cos(pos[0]) * m.UP

        vector_field = m.ArrowVectorField(func)
        self.add(vector_field)
        self.wait()

        scaled = m.VectorField.scale_func(func, 0.5)
        self.play(vector_field.animate.become(m.ArrowVectorField(scaled)))
        self.wait()
