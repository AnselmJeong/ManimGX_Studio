# Source: manim/mobject/types/point_cloud_mobject.py
import manimgx as m


class PointCloudDotExample(m.Scene):
    def construct(self):
        cloud_1 = m.PointCloudDot(color=m.RED)
        cloud_2 = m.PointCloudDot(stroke_width=4, radius=1)
        cloud_3 = m.PointCloudDot(density=15)

        group = m.Group(cloud_1, cloud_2, cloud_3).arrange()
        self.add(group)
        self.wait()
