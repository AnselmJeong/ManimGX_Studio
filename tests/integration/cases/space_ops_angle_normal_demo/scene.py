# Source: manim/utils/space_ops.py
import numpy as np

import manimgx as m
from manimgx import norm_squared, normalize_along_axis


class SpaceOpsAngleNormalDemo(m.Scene):
    def construct(self):
        # angle_of_vector: build arrows whose lengths are the angles.
        v1 = np.array([1.0, 1.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])
        a1 = m.angle_of_vector(v1)
        a2 = m.angle_of_vector(v2)
        origin = np.array([-5.0, 2.0, 0.0])
        arrow_a1 = m.Arrow(
            origin, origin + np.array([float(a1) * 1.5, 0.0, 0.0]), color=m.BLUE, buff=0
        )
        arrow_a2 = m.Arrow(
            origin + np.array([0.0, -0.5, 0.0]),
            origin + np.array([float(a2) * 1.5, -0.5, 0.0]),
            color=m.GREEN,
            buff=0,
        )

        # angle_between_vectors: angle between two vectors as a line length.
        between = m.angle_between_vectors(v1, v2)
        origin2 = np.array([-5.0, 0.5, 0.0])
        bar = m.Line(
            origin2,
            origin2 + np.array([float(between) * 1.5, 0.0, 0.0]),
            color=m.YELLOW,
            stroke_width=8,
        )

        # get_unit_normal: visualize the normal of two coplanar vectors.
        normal = m.get_unit_normal(np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]))
        normal_origin = np.array([0.0, 2.0, 0.0])
        normal_arrow = m.Arrow(
            normal_origin, normal_origin + np.asarray(normal), color=m.RED, buff=0
        )
        u_arrow = m.Arrow(
            normal_origin,
            normal_origin + np.array([1.0, 0.0, 0.0]),
            color=m.PURPLE,
            buff=0,
        )
        v_arrow = m.Arrow(
            normal_origin,
            normal_origin + np.array([0.0, 1.0, 0.0]),
            color=m.PINK,
            buff=0,
        )

        # normalize_along_axis: normalize a 3x3 row-major matrix in place,
        # then show each row as an arrow.
        rows = np.array([[3.0, 4.0, 0.0], [1.0, 1.0, 1.0], [0.0, 2.0, 0.0]])
        normalized = normalize_along_axis(rows.copy(), 1)
        row_origin = np.array([2.5, 2.0, 0.0])
        row_group = m.VGroup()
        colors = [m.BLUE, m.GREEN, m.ORANGE]
        for i, row in enumerate(normalized):
            start = row_origin + np.array([0.0, -i * 0.5, 0.0])
            row_group.add(m.Arrow(start, start + row, color=colors[i], buff=0))

        # norm_squared: place a circle whose radius is the squared norm.
        v3 = np.array([0.6, 0.8, 0.0])
        nsq = norm_squared(v3)
        nsq_circle = m.Circle(radius=float(nsq) * 0.8, color=m.WHITE).shift(
            np.array([-3.5, -2.0, 0.0])
        )

        self.add(
            arrow_a1,
            arrow_a2,
            bar,
            normal_arrow,
            u_arrow,
            v_arrow,
            row_group,
            nsq_circle,
        )
        self.wait()
