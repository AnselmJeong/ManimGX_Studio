# Source: manim/mobject/graphing/probability.py
import numpy as np

import manimgx as m


class ExampleSampleSpace(m.Scene):
    def construct(self):
        poly1 = m.SampleSpace(stroke_width=15, fill_opacity=1)
        poly2 = m.SampleSpace(width=5, height=3, stroke_width=5, fill_opacity=0.5)
        poly3 = m.SampleSpace(width=2, height=2, stroke_width=5, fill_opacity=0.1)
        poly3.divide_vertically(
            p_list=np.array([0.37, 0.13, 0.5]),
            colors=[m.BLACK, m.WHITE, m.GRAY],
            vect=m.RIGHT,
        )
        poly_group = m.VGroup(poly1, poly2, poly3).arrange()
        self.add(poly_group)
        self.wait()
