# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class StreamlinesThreeDimensionsKwarg(m.Scene):
    def construct(self):
        sl = m.StreamLines(
            lambda p: np.array([np.sin(p[1]), np.cos(p[0]), 0.0]),
            x_range=[-2, 2, 0.5],
            y_range=[-2, 2, 0.5],
            z_range=[-1, 1, 0.5],
            three_dimensions=False,
            color_scheme=lambda v: float(np.linalg.norm(v)),
            virtual_time=0.5,
            max_anchors_per_line=20,
        )
        self.add(sl)
        self.wait(0.1)
