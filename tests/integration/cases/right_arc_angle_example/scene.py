# Source: manim/mobject/geometry/line.py
import manimgx as m


class RightArcAngleExample(m.Scene):
    def construct(self):
        line1 = m.Line(m.LEFT, m.RIGHT)
        line2 = m.Line(m.DOWN, m.UP)
        rightarcangles = [
            m.Angle(line1, line2, dot=True),
            m.Angle(
                line1,
                line2,
                radius=0.4,
                quadrant=(1, -1),
                dot=True,
                other_angle=True,
            ),
            m.Angle(
                line1,
                line2,
                radius=0.5,
                quadrant=(-1, 1),
                stroke_width=8,
                dot=True,
                dot_color=m.YELLOW,
                dot_radius=0.04,
                other_angle=True,
            ),
            m.Angle(
                line1,
                line2,
                radius=0.7,
                quadrant=(-1, -1),
                color=m.RED,
                dot=True,
                dot_color=m.GREEN,
                dot_radius=0.08,
            ),
        ]
        plots = m.VGroup()
        for angle in rightarcangles:
            plot = m.VGroup(line1.copy(), line2.copy(), angle)
            plots.add(plot)
        plots.arrange(buff=1.5)
        self.add(plots)
        self.wait()
