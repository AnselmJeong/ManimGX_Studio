# Source: manim/mobject/geometry/line.py
import manimgx as m


class RightAngleExample(m.Scene):
    def construct(self):
        line1 = m.Line(m.LEFT, m.RIGHT)
        line2 = m.Line(m.DOWN, m.UP)
        rightangles = [
            m.RightAngle(line1, line2),
            m.RightAngle(line1, line2, length=0.4, quadrant=(1, -1)),
            m.RightAngle(line1, line2, length=0.5, quadrant=(-1, 1), stroke_width=8),
            m.RightAngle(line1, line2, length=0.7, quadrant=(-1, -1), color=m.RED),
        ]
        plots = m.VGroup()
        for rightangle in rightangles:
            plot = m.VGroup(line1.copy(), line2.copy(), rightangle)
            plots.add(plot)
        plots.arrange(buff=1.5)
        self.add(plots)
        self.wait()
