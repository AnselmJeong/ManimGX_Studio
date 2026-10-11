# Source: manimgx API coverage (CE 0.21 `VMobject.add_cubic_bezier_curves`)
import numpy as np

import manimgx as m


class AddCubicBezierCurvesExample(m.Scene):
    def construct(self):
        wave = m.VMobject(color=m.YELLOW, stroke_width=6)
        wave.add_cubic_bezier_curves(
            np.array(
                [
                    [[-4, 0, 0], [-3, 2, 0], [-2, -2, 0], [-1, 0, 0]],
                    [[-1, 0, 0], [0, 2, 0], [1, -2, 0], [2, 0, 0]],
                    [[2, 0, 0], [3, 2, 0], [3.5, -1, 0], [4, 0, 0]],
                ]
            )
        )
        self.play(m.Create(wave))
