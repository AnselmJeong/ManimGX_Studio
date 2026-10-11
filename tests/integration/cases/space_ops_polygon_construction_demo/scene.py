# Source: manim/utils/space_ops.py
import numpy as np

import manimgx as m


class SpaceOpsPolygonConstructionDemo(m.Scene):
    def construct(self):
        # compass_directions: build a 6-directional starburst centered left.
        dirs = m.compass_directions(6)
        start = np.array([-4.5, 1.5, 0.0])
        beam_group = m.VGroup()
        for d in dirs:
            beam_group.add(m.Line(start, start + 0.8 * d, color=m.BLUE, stroke_width=4))

        # regular_vertices (odd n): pentagonal polygon centered upper-mid.
        pent_verts, _ = m.regular_vertices(5, radius=0.9)
        pent_pts = np.asarray(pent_verts) + np.array([-1.5, 1.5, 0.0])
        pentagon = m.Polygon(*pent_pts, color=m.GREEN)

        # regular_vertices (even n): hexagon, custom start angle.
        hex_verts, _ = m.regular_vertices(6, radius=0.9, start_angle=np.pi / 12)
        hex_pts = np.asarray(hex_verts) + np.array([1.5, 1.5, 0.0])
        hexagon = m.Polygon(*hex_pts, color=m.ORANGE)

        # center_of_mass: compute the centroid of a polygon and place a dot.
        cluster_pts = np.array(
            [
                [4.0, 2.2, 0.0],
                [5.0, 2.2, 0.0],
                [5.0, 1.0, 0.0],
                [4.0, 1.0, 0.0],
                [4.5, 0.4, 0.0],
            ]
        )
        cluster_poly = m.Polygon(*cluster_pts, color=m.PURPLE)
        centroid = m.center_of_mass(cluster_pts)
        centroid_dot = m.Dot(np.asarray(centroid), color=m.RED, radius=0.1)

        # compass_directions with a non-default start vector.
        dirs2 = m.compass_directions(8, start_vect=np.array([0.6, 0.6, 0.0]))
        start2 = np.array([-3.0, -2.0, 0.0])
        beam_group2 = m.VGroup()
        for d in dirs2:
            beam_group2.add(m.Line(start2, start2 + d, color=m.PINK, stroke_width=3))

        # regular_vertices small radius polygon.
        tri_verts, _ = m.regular_vertices(3, radius=0.6)
        tri_pts = np.asarray(tri_verts) + np.array([3.0, -2.0, 0.0])
        triangle = m.Polygon(*tri_pts, color=m.YELLOW)

        self.add(
            beam_group,
            pentagon,
            hexagon,
            cluster_poly,
            centroid_dot,
            beam_group2,
            triangle,
        )
        self.wait()
