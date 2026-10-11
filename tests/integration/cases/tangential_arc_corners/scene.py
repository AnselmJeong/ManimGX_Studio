# Source: manim/mobject/geometry/arc.py
import numpy as np

import manimgx as m


def line_intersection(line1, line2):
    s1 = np.asarray(line1.get_start(), dtype=float)
    e1 = np.asarray(line1.get_end(), dtype=float)
    s2 = np.asarray(line2.get_start(), dtype=float)
    e2 = np.asarray(line2.get_end(), dtype=float)

    x1, y1 = s1[:2]
    x2, y2 = e1[:2]
    x3, y3 = s2[:2]
    x4, y4 = e2[:2]

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return (s1 + e1) / 2

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return np.array([x1 + t * (x2 - x1), y1 + t * (y2 - y1), 0.0])


def get_unit_vector(line):
    start = np.asarray(line.get_start(), dtype=float)
    end = np.asarray(line.get_end(), dtype=float)
    vector = end - start
    return vector / np.linalg.norm(vector)


def tangential_arc(line1, line2, radius, corner=(1, 1), **kwargs):
    intersection_point = line_intersection(line1, line2)

    s1, s2 = corner
    unit_vector1 = s1 * get_unit_vector(line1)
    unit_vector2 = s2 * get_unit_vector(line2)

    dot = np.dot(unit_vector1, unit_vector2)
    corner_angle = np.arccos(np.clip(dot, -1.0, 1.0))
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


class TangentialArcCorners(m.Scene):
    def construct(self):
        # Create two intersecting lines
        line1 = m.DashedLine(start=3 * m.LEFT, end=3 * m.RIGHT, color=m.GREY)
        line2 = m.DashedLine(start=3 * m.UP, end=3 * m.DOWN, color=m.GREY)

        # All four corner configurations with different colors
        arc_pp = tangential_arc(line1, line2, radius=1.5, corner=(1, 1), color=m.RED)
        arc_pn = tangential_arc(line1, line2, radius=1.5, corner=(1, -1), color=m.GREEN)
        arc_np = tangential_arc(line1, line2, radius=1.5, corner=(-1, 1), color=m.BLUE)
        arc_nn = tangential_arc(
            line1, line2, radius=1.5, corner=(-1, -1), color=m.YELLOW
        )

        # Labels for each arc
        label_pp = m.Text("(1,1)", font_size=24, color=m.RED).next_to(
            arc_pp,
            m.UR,
            buff=0.1,
        )
        label_pn = m.Text("(1,-1)", font_size=24, color=m.GREEN).next_to(
            arc_pn,
            m.DR,
            buff=0.1,
        )
        label_np = m.Text("(-1,1)", font_size=24, color=m.BLUE).next_to(
            arc_np,
            m.UL,
            buff=0.1,
        )
        label_nn = m.Text("(-1,-1)", font_size=24, color=m.YELLOW).next_to(
            arc_nn,
            m.DL,
            buff=0.1,
        )

        self.add(line1, line2, arc_pp, arc_pn, arc_np, arc_nn)
        self.add(label_pp, label_pn, label_np, label_nn)
