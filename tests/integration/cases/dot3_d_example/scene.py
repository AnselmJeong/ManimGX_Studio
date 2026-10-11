# Source: manim/mobject/three_d/three_dimensions.py
import manimgx as m


class Dot3DExample(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=-45 * m.DEGREES)

        axes = m.ThreeDAxes()
        dot_1 = m.Dot3D(point=axes.coords_to_point(0, 0, 1), color=m.RED)
        dot_2 = m.Dot3D(point=axes.coords_to_point(2, 0, 0), radius=0.1, color=m.BLUE)
        dot_3 = m.Dot3D(point=[0, 0, 0], radius=0.1, color=m.ORANGE)
        self.add(axes, dot_1, dot_2, dot_3)
        self.wait()
