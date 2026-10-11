# Source: manim/mobject/geometry/line.py
import manimgx as m


class AngleExample(m.Scene):
    def construct(self):
        line1 = m.Line(m.LEFT + (1 / 3) * m.UP, m.RIGHT + (1 / 3) * m.DOWN)
        line2 = m.Line(m.DOWN + (1 / 3) * m.RIGHT, m.UP + (1 / 3) * m.LEFT)
        angles = [
            m.Angle(line1, line2),
            m.Angle(line1, line2, radius=0.4, quadrant=(1, -1), other_angle=True),
            m.Angle(
                line1,
                line2,
                radius=0.5,
                quadrant=(-1, 1),
                stroke_width=8,
                other_angle=True,
            ),
            m.Angle(line1, line2, radius=0.7, quadrant=(-1, -1), color=m.RED),
            m.Angle(line1, line2, other_angle=True),
            m.Angle(line1, line2, radius=0.4, quadrant=(1, -1)),
            m.Angle(line1, line2, radius=0.5, quadrant=(-1, 1), stroke_width=8),
            m.Angle(
                line1,
                line2,
                radius=0.7,
                quadrant=(-1, -1),
                color=m.RED,
                other_angle=True,
            ),
        ]
        plots = m.VGroup()
        for angle in angles:
            plot = m.VGroup(line1.copy(), line2.copy(), angle)
            plots.add(m.VGroup(plot, m.SurroundingRectangle(plot, buff=0.3)))
        plots.arrange_in_grid(rows=2, buff=1)
        self.add(plots)
        self.wait()
