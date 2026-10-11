# Many see-through points on nearly one spot, a see-through line through them, the camera
# turning: the pile, however deep, lies over the line where its points are nearer.
import numpy as np

import manimgx as m


class PileOfSeeThroughPointsOnALine(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=60 * m.DEGREES, theta=-45 * m.DEGREES)
        rng = np.random.default_rng(3)
        spot = [0.0, 0.0, 1.0] + rng.normal(scale=0.15, size=(800, 3))
        pile = m.PMobject(stroke_width=12)
        pile.add_points(spot, color=m.ORANGE, alpha=0.3)
        line = m.Line([-3, 0, 1], [3, 0, 1], stroke_width=10, color=m.BLUE).set_stroke(
            opacity=0.7
        )
        self.add(pile, line)
        self.begin_ambient_camera_rotation(rate=0.6)
        self.wait(2)
