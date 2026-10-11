# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class ThreeDAxesZAxisConfigExample(m.ThreeDScene):
    def construct(self):
        ax = m.ThreeDAxes(z_axis_config={"stroke_width": 3, "tick_size": 0.15})
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=40 * m.DEGREES)
        self.add(ax)
        self.wait()
