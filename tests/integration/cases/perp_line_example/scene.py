# Source: manim/mobject/three_d/three_dimensions.py
import manimgx as m


class PerpLineExample(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(m.PI / 3, -m.PI / 4)
        ax = m.ThreeDAxes((-5, 5, 1), (-5, 5, 1), (-5, 5, 1), 10, 10, 10)
        line1 = m.Line3D(m.RIGHT * 2, m.UP + m.OUT, color=m.RED)
        line2 = m.Line3D.perpendicular_to(line1, color=m.BLUE)
        self.add(ax, line1, line2)
