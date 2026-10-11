# Source: manim/utils/space_ops.py
import numpy as np

import manimgx as m


class SpaceOpsIntersectionDemo(m.Scene):
    def construct(self):
        # line_intersection: two crossing lines and their intersection point.
        p1 = np.array([-5.0, -1.0, 0.0])
        p2 = np.array([-2.0, 2.0, 0.0])
        p3 = np.array([-5.0, 2.0, 0.0])
        p4 = np.array([-2.0, -1.0, 0.0])
        line1 = m.Line(p1, p2, color=m.BLUE, stroke_width=4)
        line2 = m.Line(p3, p4, color=m.GREEN, stroke_width=4)
        intersect = m.line_intersection([p1, p2], [p3, p4])
        intersect_dot = m.Dot(np.asarray(intersect), color=m.RED, radius=0.12)

        # perpendicular_bisector: bisector of a segment.
        seg_a = np.array([0.5, 1.5, 0.0])
        seg_b = np.array([2.5, 1.5, 0.0])
        segment = m.Line(seg_a, seg_b, color=m.PURPLE, stroke_width=4)
        bis = m.perpendicular_bisector([seg_a, seg_b])
        bisector = m.Line(
            np.asarray(bis[0]), np.asarray(bis[1]), color=m.ORANGE, stroke_width=4
        )

        # find_intersection: closest points between two skew lines (here we
        # use coplanar lines so the result equals their intersection).
        p0 = np.array([3.5, 0.0, 0.0])
        v0 = np.array([1.0, 1.0, 0.0])
        q0 = np.array([5.0, 2.0, 0.0])
        v1 = np.array([1.0, -1.0, 0.0])
        result = m.find_intersection([p0], [v0], [q0], [v1])
        l1 = m.Line(p0 - v0, p0 + 1.5 * v0, color=m.YELLOW, stroke_width=4)
        l2 = m.Line(q0 - v1, q0 + 1.5 * v1, color=m.PINK, stroke_width=4)
        result_dot = m.Dot(np.asarray(result[0]), color=m.WHITE, radius=0.12)

        # cross2d: scale a polygon by abs(cross2d) of two vectors.
        a = np.array([1.0, 2.0])
        b = np.array([3.0, 4.0])
        c2d = float(m.cross2d(a, b))
        scaled = m.Square(side_length=abs(c2d) * 0.3, color=m.WHITE).shift(
            np.array([-3.5, -2.0, 0.0])
        )

        # cross2d batched: visualize as colored squares stacked vertically.
        a_batch = np.array([[1.0, 2.0, 0.0], [3.0, 0.0, 0.0]])
        b_batch = np.array([[3.0, 4.0, 0.0], [0.0, 4.0, 0.0]])
        c2d_batched = m.cross2d(a_batch, b_batch)
        batch_group = m.VGroup()
        for i, val in enumerate(np.asarray(c2d_batched)):
            color = m.GREEN if float(val) > 0 else m.RED
            sq = m.Square(
                side_length=abs(float(val)) * 0.15 + 0.1, color=color, fill_opacity=1
            )
            sq.shift(np.array([0.0, -2.0 - i * 0.6, 0.0]))
            batch_group.add(sq)

        self.add(
            line1,
            line2,
            intersect_dot,
            segment,
            bisector,
            l1,
            l2,
            result_dot,
            scaled,
            batch_group,
        )
        self.wait()
