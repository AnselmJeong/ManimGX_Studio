# Source: manim/animation/transform.py
import numpy as np

import manimgx as m


class TransformPathArcCentersExample(m.Scene):
    def construct(self):
        source = m.Square(color=m.BLUE, fill_opacity=1.0).shift(2 * m.LEFT)
        target = m.Square(color=m.RED, fill_opacity=1.0).shift(2 * m.RIGHT)
        self.add(source)
        self.play(
            m.Transform(
                source,
                target,
                path_arc=m.PI,
                path_arc_centers=np.array([0.0, 0.0, 0.0]),
            )
        )
