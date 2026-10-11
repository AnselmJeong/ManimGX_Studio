# Source: manim/mobject/table.py
import numpy as np

import manimgx as m


class DecimalTableExample(m.Scene):
    def construct(self):
        x_vals = [-2, -1, 0, 1, 2]
        y_vals = np.exp(x_vals)
        t0 = m.DecimalTable(
            [x_vals, y_vals],
            row_labels=[m.MathTex("x"), m.MathTex("f(x)=e^{x}")],
            h_buff=1,
            element_to_mobject_config={"num_decimal_places": 2},
        )
        self.add(t0)
        self.wait()
