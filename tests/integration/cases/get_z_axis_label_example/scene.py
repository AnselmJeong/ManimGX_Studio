# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetZAxisLabelExample(m.ThreeDScene):
    def construct(self):
        ax = m.ThreeDAxes()
        lab = ax.get_z_axis_label(m.Tex("$z$-label"))
        self.set_camera_orientation(phi=2 * m.PI / 5, theta=m.PI / 5)
        self.add(ax, lab)
        self.wait()
