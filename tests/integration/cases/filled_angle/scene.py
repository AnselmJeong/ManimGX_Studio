# Source: manim/mobject/geometry/line.py
import numpy as np

import manimgx as m


class FilledAngle(m.Scene):
    def construct(self):
        l1 = m.Line(m.ORIGIN, 2 * m.UP + m.RIGHT).set_color(m.GREEN)
        l2 = (
            m.Line(m.ORIGIN, 2 * m.UP + m.RIGHT)
            .set_color(m.GREEN)
            .rotate(-20 * m.DEGREES, about_point=m.ORIGIN)
        )
        norm = l1.get_length()
        a1 = m.Angle(l1, l2, other_angle=True, radius=norm - 0.5).set_color(m.GREEN)
        a2 = m.Angle(l1, l2, other_angle=True, radius=norm).set_color(m.GREEN)
        q1 = a1.points  #  save all coordinates of points of angle a1
        q2 = (
            a2.reverse_direction().points
        )  #  save all coordinates of points of angle a1 (in reversed direction)
        pnts = np.concatenate(
            [q1, q2, q1[0].reshape(1, 3)]
        )  # adds points and ensures that path starts and ends at same point
        mfill = m.VMobject().set_color(m.ORANGE)
        mfill.set_points_as_corners(pnts).set_fill(m.GREEN, opacity=1)
        self.add(l1, l2)
        self.add(mfill)
        self.wait()
