# Source: manim/mobject/three_d/three_dimensions.py
import manimgx as m


class ExampleCone(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        cone = m.Cone(direction=m.X_AXIS + m.Y_AXIS + 2 * m.Z_AXIS, resolution=8)
        self.set_camera_orientation(phi=5 * m.PI / 11, theta=m.PI / 9)
        self.add(axes, cone)
        self.wait()
