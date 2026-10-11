# Source: manimgx API coverage (CE 0.21 `LinearTransformationScene.apply_nonlinear_transformation`)
import numpy as np

import manimgx as m


class NonlinearTransformationExample(m.LinearTransformationScene):
    def construct(self):
        self.add_moving_mobject(m.Dot([1, 1, 0], color=m.RED))
        self.apply_nonlinear_transformation(
            lambda p: p + np.array([np.sin(p[1]), np.sin(p[0]), 0])
        )
        self.wait(0.5)
