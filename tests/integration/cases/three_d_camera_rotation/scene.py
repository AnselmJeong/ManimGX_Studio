# Source: docs/source/examples.rst
import manimgx as m


class ThreeDCameraRotation(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        circle = m.Circle()
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(circle, axes)
        self.begin_ambient_camera_rotation(rate=0.1)
        self.wait()
        self.stop_ambient_camera_rotation()
        self.move_camera(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        self.wait()
