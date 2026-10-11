# Source: manim/mobject/three_d/three_dimensions.py
import manimgx as m


class ExampleTorus(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        torus = m.Torus()
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(axes, torus)
        self.wait()
