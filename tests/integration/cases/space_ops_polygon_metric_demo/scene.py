# Source: manim/utils/space_ops.py
import numpy as np

import manimgx as m


class SpaceOpsPolygonMetricDemo(m.Scene):
    def construct(self):
        # shoelace: signed area of a CCW square sets the side length of a
        # demonstration square.
        ccw_verts = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
        ccw_area = m.shoelace(ccw_verts)
        ccw_disp_color = m.GREEN if abs(ccw_area) > 0.5 else m.RED
        ccw_square = m.Square(
            side_length=abs(ccw_area) * 0.9, color=ccw_disp_color
        ).shift(np.array([-4.5, 2.0, 0.0]))

        # shoelace_direction: build a CW polygon and a CCW one, color the
        # demonstration squares accordingly.
        cw_verts = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])
        cw_dir = m.shoelace_direction(cw_verts)
        ccw_dir = m.shoelace_direction(ccw_verts)
        cw_color = m.RED if cw_dir == "CW" else m.BLUE
        ccw_color = m.GREEN if ccw_dir == "CCW" else m.YELLOW
        cw_sq = m.Square(side_length=0.6, color=cw_color, fill_opacity=1).shift(
            np.array([-2.5, 2.0, 0.0])
        )
        ccw_sq = m.Square(side_length=0.6, color=ccw_color, fill_opacity=1).shift(
            np.array([-1.5, 2.0, 0.0])
        )

        # get_winding_number: square around origin has winding 1, square
        # offset away from origin has winding 0.
        winding_origin = [
            np.array([1.0, 1.0, 0.0]),
            np.array([-1.0, 1.0, 0.0]),
            np.array([-1.0, -1.0, 0.0]),
            np.array([1.0, -1.0, 0.0]),
        ]
        winding_offset = [
            np.array([3.0, 3.0, 0.0]),
            np.array([2.0, 3.0, 0.0]),
            np.array([2.0, 2.0, 0.0]),
            np.array([3.0, 2.0, 0.0]),
        ]
        w1 = m.get_winding_number(winding_origin)
        w2 = m.get_winding_number(winding_offset)
        bar1 = m.Line(
            np.array([0.5, 1.0, 0.0]),
            np.array([0.5 + float(w1), 1.0, 0.0]),
            color=m.BLUE,
            stroke_width=10,
        )
        bar2 = m.Line(
            np.array([0.5, 0.4, 0.0]),
            np.array([0.5 + float(w2) + 0.1, 0.4, 0.0]),
            color=m.PURPLE,
            stroke_width=10,
        )

        # earclip_triangulation: triangulate a concave pentagon and draw
        # the resulting triangles.
        verts2d = np.array(
            [
                [-0.5, -1.5, 0.0],
                [0.5, -1.5, 0.0],
                [0.7, -0.5, 0.0],
                [0.0, 0.0, 0.0],
                [-0.7, -0.5, 0.0],
            ]
        )
        tri_indices = m.earclip_triangulation(verts2d, [5])
        tri_group = m.VGroup()
        colors = [m.BLUE, m.GREEN, m.RED, m.ORANGE, m.PURPLE]
        offset = np.array([3.0, -1.5, 0.0])
        for k in range(0, len(tri_indices), 3):
            i0, i1, i2 = tri_indices[k], tri_indices[k + 1], tri_indices[k + 2]
            color = colors[(k // 3) % len(colors)]
            tri = m.Polygon(
                verts2d[i0] + offset,
                verts2d[i1] + offset,
                verts2d[i2] + offset,
                color=color,
                fill_opacity=0.6,
            )
            tri_group.add(tri)

        self.add(ccw_square, cw_sq, ccw_sq, bar1, bar2, tri_group)
        self.wait()
