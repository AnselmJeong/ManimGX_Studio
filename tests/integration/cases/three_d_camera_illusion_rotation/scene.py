# Source: docs/source/examples.rst
import manimgx as m


class ThreeDCameraIllusionRotation(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        circle = m.Circle()
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(circle, axes)
        self.begin_3dillusion_camera_rotation(rate=2)
        self.wait(m.PI / 2)
        self.stop_3dillusion_camera_rotation()
