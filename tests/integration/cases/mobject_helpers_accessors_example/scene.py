# Source: manim/mobject/mobject.py
import numpy as np

import manimgx as m


class MobjectHelpersAccessorsExample(m.Scene):
    def construct(self):
        # Asymmetric polygon: vertex centroid is (0, 1/6, 0), AABB center is
        # (0, 0.5, 0). A symmetric shape (Square/Circle) hides bugs where
        # `get_center_of_mass` returns the AABB center instead of the actual
        # mean of the path's control points.
        anchor = m.Polygon([-1.0, -0.5, 0.0], [1.0, -0.5, 0.0], [0.0, 1.5, 0.0])
        anchor.set_color(m.YELLOW)
        self.add(anchor)

        expected_centroid = np.array([0.0, 1.0 / 6.0, 0.0])
        actual_centroid = np.asarray(anchor.get_center_of_mass(), dtype=float)
        assert np.allclose(actual_centroid, expected_centroid, atol=1e-3), (
            f"COM mismatch: got {actual_centroid}, expected {expected_centroid}"
        )
        aabb_center = np.asarray(anchor.get_center(), dtype=float)
        assert not np.allclose(actual_centroid, aabb_center, atol=1e-3), (
            "COM should differ from AABB center for asymmetric shape; "
            f"got com={actual_centroid}, aabb={aabb_center}"
        )

        target = m.Circle().to_edge(m.RIGHT)
        target.set_color(m.BLUE)
        self.add(target)

        follower = m.Triangle().scale(0.5)
        follower.match_color(target)
        follower.match_width(target)
        follower.match_height(target)
        follower.match_depth(target)
        follower.match_dim_size(target, 0)
        follower.match_coord(target, 0)
        follower.match_x(target)
        follower.match_y(target)
        follower.match_z(target)
        self.add(follower)

        edge_dot = m.Dot(anchor.get_edge_center(m.RIGHT)).set_color(m.RED)
        zenith_dot = m.Dot(anchor.get_zenith()).set_color(m.GREEN)
        nadir_dot = m.Dot(anchor.get_nadir()).set_color(m.PURPLE)
        com_dot = m.Dot(anchor.get_center_of_mass()).set_color(m.ORANGE)
        boundary_dot = m.Dot(anchor.get_boundary_point(m.UP)).set_color(m.PINK)
        self.add(edge_dot, zenith_dot, nadir_dot, com_dot, boundary_dot)

        readout = m.Text(
            f"x={round(anchor.get_x(), 2)} "
            f"y={round(anchor.get_y(), 2)} "
            f"z={round(anchor.get_z(), 2)} "
            f"coord0={round(anchor.get_coord(0), 2)}",
            font_size=18,
        ).to_corner(m.UR)
        self.add(readout)

        mover = m.Square(side_length=0.8).set_color(m.WHITE)
        mover.set_coord(2.0, 0, direction=m.LEFT)
        mover.set_x(-2.0, direction=m.LEFT)
        mover.set_y(1.0, direction=m.UP)
        mover.set_z(0.0, direction=m.OUT)
        self.add(mover)

        alpha = anchor.proportion_from_point(anchor.point_from_proportion(0.5))
        proportion_label = m.Text(f"alpha={round(alpha, 2)}", font_size=18).to_corner(
            m.UL
        )
        self.add(proportion_label)

        self.wait()
