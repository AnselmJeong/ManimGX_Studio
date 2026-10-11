# Source: manim/mobject/three_d/three_dimensions.py
import manimgx as m


class CubeExample(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=-45 * m.DEGREES)

        axes = m.ThreeDAxes()
        cube = m.Cube(side_length=3, fill_opacity=0.7, fill_color=m.BLUE)
        self.add(cube)
        self.wait()
