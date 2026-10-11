# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetAxisLabelsExample(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=2 * m.PI / 5, theta=m.PI / 5)
        axes = m.ThreeDAxes()
        labels = axes.get_axis_labels(
            m.Text("x-axis").scale(0.7),
            m.Text("y-axis").scale(0.45),
            m.Text("z-axis").scale(0.45),
        )
        self.add(axes, labels)
        self.wait()
