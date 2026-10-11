# Source: manim/mobject/types/point_cloud_mobject.py
import manimgx as m


class PgroupExample(m.Scene):
    def construct(self):

        p1 = m.PointCloudDot(radius=1, density=20, color=m.BLUE)
        p1.move_to(4.5 * m.LEFT)
        p2 = m.PointCloudDot()
        p3 = m.PointCloudDot(radius=1.5, stroke_width=2.5, color=m.PINK)
        p3.move_to(4.5 * m.RIGHT)
        pList = m.PGroup(p1, p2, p3)

        self.add(pList)
        self.wait()
