# Source: manim/utils/space_ops.py
import numpy as np

import manimgx as m
from manimgx import rotation_matrix_transpose


class SpaceOpsRotationDemo(m.Scene):
    def construct(self):
        # rotation_about_z: rotate a square by 30 degrees.
        rot_z = m.rotation_about_z(np.pi / 6)
        base_pts = np.array(
            [[0.6, 0.0, 0.0], [0.0, 0.6, 0.0], [-0.6, 0.0, 0.0], [0.0, -0.6, 0.0]]
        )
        rotated = np.array([rot_z @ p for p in base_pts]) + np.array([-4.5, 1.8, 0.0])
        rotated_poly = m.Polygon(*rotated, color=m.BLUE)

        # rotate_vector: rotate a vector via the helper.
        v = np.array([1.2, 0.0, 0.0])
        v_rot = m.rotate_vector(v, np.pi / 3)
        origin = np.array([-1.8, 1.8, 0.0])
        arrow_a = m.Arrow(origin, origin + v, color=m.YELLOW, buff=0)
        arrow_b = m.Arrow(origin, origin + v_rot, color=m.GREEN, buff=0)

        # z_to_vector: derive a basis that maps +Z to a given direction.
        target_dir = np.array([1.0, 1.0, 0.5])
        basis = m.z_to_vector(target_dir)
        local_z = basis @ np.array([0.0, 0.0, 1.0])
        local_z = local_z / np.linalg.norm(local_z)
        arrow_z = m.Arrow(
            np.array([1.8, 1.8, 0.0]),
            np.array([1.8, 1.8, 0.0]) + local_z,
            color=m.RED,
            buff=0,
        )

        # thick_diagonal: visualize an integer matrix as colored squares.
        td = m.thick_diagonal(5, thickness=2)
        cells = m.VGroup()
        cell_size = 0.3
        origin2 = np.array([4.0, 2.6, 0.0])
        for i in range(5):
            for j in range(5):
                color = m.WHITE if td[i, j] == 1 else m.DARK_GRAY
                sq = m.Square(side_length=cell_size, color=color, fill_opacity=1)
                sq.move_to(origin2 + np.array([j * cell_size, -i * cell_size, 0.0]))
                cells.add(sq)

        # rotation_matrix_transpose: rotation about a non-Z axis, transposed.
        rmt = rotation_matrix_transpose(np.pi / 4, np.array([0.0, 0.0, 1.0]))
        rmt_pts = np.array([rmt @ p for p in base_pts]) + np.array([-4.5, -1.6, 0.0])
        rmt_poly = m.Polygon(*rmt_pts, color=m.PURPLE)

        self.add(rotated_poly, arrow_a, arrow_b, arrow_z, cells, rmt_poly)
        self.wait()
