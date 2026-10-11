# Source: manim/utils/polylabel.py
import numpy as np

import manimgx as m
from manimgx import polylabel


class PolylabelPoleExample(m.Scene):
    def construct(self):
        ring = np.array(
            [[-2.0, -1.0, 0.0], [2.0, -1.0, 0.0], [2.0, 1.0, 0.0], [-2.0, 1.0, 0.0]]
        )
        outline = m.Polygon(*ring, color=m.BLUE)
        pole_cell = polylabel([ring], precision=0.01)
        pole_dot = m.Dot(
            np.array([pole_cell.c[0], pole_cell.c[1], 0.0]), color=m.YELLOW
        )
        self.add(outline, pole_dot)
        self.wait()
