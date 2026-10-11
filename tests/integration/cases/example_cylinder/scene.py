# Source: manim/mobject/three_d/three_dimensions.py
import manimgx as m


class ExampleCylinder(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        cylinder = m.Cylinder(radius=2, height=3)
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(axes, cylinder)
        self.wait()
