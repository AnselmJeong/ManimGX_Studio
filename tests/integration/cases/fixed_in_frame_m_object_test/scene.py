# Source: docs/source/examples.rst
import manimgx as m


class FixedInFrameMObjectTest(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=-45 * m.DEGREES)
        text3d = m.Text("This is a 3D text")
        self.add_fixed_in_frame_mobjects(text3d)
        text3d.to_corner(m.UL)
        self.add(axes)
        self.wait()
