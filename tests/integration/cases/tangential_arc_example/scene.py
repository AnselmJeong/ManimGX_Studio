# Source: manim/mobject/geometry/arc.py
import numpy as np

import manimgx as m


def make_tangential_arc(line1, line2, radius, corner=(1, 1), **kwargs):
    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    start1, end1 = line1.get_start(), line1.get_end()
    start2, end2 = line2.get_start(), line2.get_end()
    xdiff = np.array([start1[0] - end1[0], start2[0] - end2[0]])
    ydiff = np.array([start1[1] - end1[1], start2[1] - end2[1]])
    div = det(xdiff, ydiff)
    d = np.array([det(start1, end1), det(start2, end2)])
    intersection_point = np.array([det(d, xdiff) / div, det(d, ydiff) / div, 0])

    s1, s2 = corner
    unit_vector1 = s1 * (end1 - start1) / np.linalg.norm(end1 - start1)
    unit_vector2 = s2 * (end2 - start2) / np.linalg.norm(end2 - start2)

    dot_product = np.dot(unit_vector1, unit_vector2)
    corner_angle = np.arccos(np.clip(dot_product, -1, 1))
    tangent_point_distance = radius / np.tan(corner_angle / 2)

    tangent_point1 = intersection_point + tangent_point_distance * unit_vector1
    tangent_point2 = intersection_point + tangent_point_distance * unit_vector2

    cross_product = (
        unit_vector1[0] * unit_vector2[1] - unit_vector1[1] * unit_vector2[0]
    )
    if cross_product < 0:
        start_point = tangent_point1
        end_point = tangent_point2
    else:
        start_point = tangent_point2
        end_point = tangent_point1

    return m.ArcBetweenPoints(start=start_point, end=end_point, radius=radius, **kwargs)


class TangentialArcExample(m.Scene):
    def construct(self):
        line1 = m.DashedLine(start=3 * m.LEFT, end=3 * m.RIGHT)
        line1.rotate(angle=31 * m.DEGREES, about_point=m.ORIGIN)
        line2 = m.DashedLine(start=3 * m.UP, end=3 * m.DOWN)
        line2.rotate(angle=12 * m.DEGREES, about_point=m.ORIGIN)

        arc = make_tangential_arc(
            line1, line2, radius=2.25, corner=(1, 1), color=m.TEAL
        )
        self.add(arc, line1, line2)
