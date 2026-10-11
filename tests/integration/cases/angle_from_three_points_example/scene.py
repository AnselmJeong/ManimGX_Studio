# Source: manim/mobject/geometry/line.py
import manimgx as m


class AngleFromThreePointsExample(m.Scene):
    def construct(self):
        sample_angle = m.Angle.from_three_points(m.UP, m.ORIGIN, m.LEFT)
        red_angle = m.Angle.from_three_points(
            m.LEFT + m.UP,
            m.ORIGIN,
            m.RIGHT,
            radius=0.8,
            quadrant=(-1, -1),
            color=m.RED,
            stroke_width=8,
            other_angle=True,
        )
        self.add(red_angle, sample_angle)
        self.wait()
