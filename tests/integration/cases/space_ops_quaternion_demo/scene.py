# Source: manim/utils/space_ops.py
import numpy as np

import manimgx as m
from manimgx import (
    rotation_matrix_from_quaternion,
    rotation_matrix_transpose_from_quaternion,
)


class SpaceOpsQuaternionDemo(m.Scene):
    def construct(self):
        # Build a quaternion from angle+axis, then derive a rotation matrix
        # and apply it to a triangle.
        q1 = m.quaternion_from_angle_axis(np.pi / 3, np.array([0.0, 0.0, 1.0]))
        R1 = rotation_matrix_from_quaternion(np.asarray(q1, dtype=float))
        tri_pts = np.array([[0.7, 0.0, 0.0], [-0.4, 0.6, 0.0], [-0.4, -0.6, 0.0]])
        rotated1 = np.array([R1[:3, :3] @ p for p in tri_pts]) + np.array(
            [-4.5, 1.8, 0.0]
        )
        tri1 = m.Polygon(*rotated1, color=m.BLUE)

        # quaternion_mult: apply two successive rotations as one quaternion.
        q2 = m.quaternion_from_angle_axis(np.pi / 4, np.array([0.0, 0.0, 1.0]))
        q12 = m.quaternion_mult(q1, q2)
        R12 = rotation_matrix_from_quaternion(np.asarray(q12, dtype=float))
        rotated2 = np.array([R12[:3, :3] @ p for p in tri_pts]) + np.array(
            [-1.8, 1.8, 0.0]
        )
        tri2 = m.Polygon(*rotated2, color=m.GREEN)

        # quaternion_conjugate: applying the conjugate undoes the rotation.
        q1_arr = np.asarray(q1, dtype=float)
        q1_conj = m.quaternion_conjugate(q1_arr)
        q_identity = m.quaternion_mult(q1_arr, q1_conj)
        R_id = rotation_matrix_from_quaternion(np.asarray(q_identity, dtype=float))
        identity_pts = np.array([R_id[:3, :3] @ p for p in tri_pts]) + np.array(
            [1.8, 1.8, 0.0]
        )
        tri_id = m.Polygon(*identity_pts, color=m.YELLOW)

        # angle_axis_from_quaternion: recover the angle, draw arrows whose
        # length matches the recovered angle.
        angle, axis = m.angle_axis_from_quaternion(q1_arr)
        len_arrow = float(angle) * 0.6
        origin = np.array([4.5, 1.8, 0.0])
        arrow = m.Arrow(
            origin, origin + np.array([len_arrow, 0.0, 0.0]), color=m.RED, buff=0
        )
        axis_arrow = m.Arrow(
            origin + np.array([0.0, -0.5, 0.0]),
            origin + np.array([0.0, -0.5, 0.0]) + 0.6 * np.asarray(axis),
            color=m.PURPLE,
            buff=0,
        )

        # rotation_matrix_transpose_from_quaternion: rotate the basis the
        # other way and visualize as a polygon.
        rows = rotation_matrix_transpose_from_quaternion(q1_arr)
        R_T = np.array(rows)
        rotated3 = np.array([R_T @ p for p in tri_pts]) + np.array([-4.5, -1.8, 0.0])
        tri3 = m.Polygon(*rotated3, color=m.ORANGE)

        # Compose multiple quaternion products to spin a polygon several
        # times.
        q_step = m.quaternion_from_angle_axis(np.pi / 6, np.array([0.0, 0.0, 1.0]))
        q_total = m.quaternion_mult(q_step, q_step, q_step)
        R_total = rotation_matrix_from_quaternion(np.asarray(q_total, dtype=float))
        rotated4 = np.array([R_total[:3, :3] @ p for p in tri_pts]) + np.array(
            [-1.8, -1.8, 0.0]
        )
        tri4 = m.Polygon(*rotated4, color=m.PINK)

        self.add(tri1, tri2, tri_id, arrow, axis_arrow, tri3, tri4)
        self.wait()
