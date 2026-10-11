# See-through points inside a see-through sphere, the camera turning: every point shows over
# the sphere's far side and under its near side.
import numpy as np

import manimgx as m


class CloudInsideASeeThroughSphere(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=-30 * m.DEGREES)
        rng = np.random.default_rng(2)
        directions = rng.normal(size=(1200, 3))
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        inside = directions * 1.6 * rng.random((1200, 1)) ** (1 / 3)
        cloud = m.PMobject(stroke_width=8)
        cloud.add_points(inside, color=m.YELLOW, alpha=0.6)
        sphere = m.Sphere(radius=2, resolution=(24, 12)).set_fill(m.BLUE, 0.35)
        sphere.set_stroke(width=0)
        self.add(sphere, cloud)
        self.begin_ambient_camera_rotation(rate=0.6)
        self.wait(2)
