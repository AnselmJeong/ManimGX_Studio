# A see-through cloud of points cut by a see-through plane, a line through both, the camera
# turning: each point shows over the plane and the line where it is nearer, under them where
# it is farther.
import numpy as np

import manimgx as m


class SeeThroughCloudCutByAPlane(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-40 * m.DEGREES)
        rng = np.random.default_rng(1)
        cloud = m.PMobject(stroke_width=8)
        cloud.add_points(
            rng.normal(scale=0.9, size=(1500, 3)), color=m.YELLOW, alpha=0.45
        )
        plane = m.Square(side_length=4).set_fill(m.BLUE, 0.5).set_stroke(width=0)
        plane.rotate(90 * m.DEGREES, m.RIGHT)
        line = m.Line([-3, 0, -1], [3, 0, 1], stroke_width=8, color=m.RED).set_stroke(
            opacity=0.8
        )
        self.add(cloud, plane, line)
        self.begin_ambient_camera_rotation(rate=0.6)
        self.wait(2)
