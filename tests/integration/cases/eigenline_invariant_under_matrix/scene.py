"""What's an eigenvector of [[3, 1], [0, 2]]? Show what happens to the eigenline when you apply the matrix."""

import numpy as np

import manimgx as m

MAT = np.array([[3.0, 1.0], [0.0, 2.0]])


def _normalized_eigenvectors() -> tuple[np.ndarray, np.ndarray]:
    """Return the two eigenvectors of MAT as unit-length 3D vectors (z=0).

    For [[3, 1], [0, 2]], eigenvalues are 3 and 2; eigenvectors are (1, 0) and (1, -1)/sqrt(2).
    """
    eigvals, eigvecs = np.linalg.eig(MAT)
    # eigvecs is column-wise; sort so first is the larger eigenvalue.
    order = np.argsort(-eigvals)
    v1 = eigvecs[:, order[0]]
    v2 = eigvecs[:, order[1]]
    v1 = v1 / np.linalg.norm(v1)
    v2 = v2 / np.linalg.norm(v2)
    return (
        np.array([float(v1[0]), float(v1[1]), 0.0]),
        np.array([float(v2[0]), float(v2[1]), 0.0]),
    )


class TeacherScene(m.Scene):
    def construct(self):
        # NumberPlane scaled to keep the eigenlines inside the safe zone even after applying MAT.
        plane = m.NumberPlane(
            x_range=(-4, 4, 1),
            y_range=(-3, 3, 1),
        ).scale(0.65)

        # Two eigen-directions: TEAL for lambda = 3, YELLOW for lambda = 2.
        v_large, v_small = _normalized_eigenvectors()

        # Fat colored lines through the origin along each eigen-direction.
        line_large = m.Line(
            start=(-v_large * 3.2).tolist(),
            end=(v_large * 3.2).tolist(),
            color=m.TEAL,
            stroke_width=7.0,
        )
        line_small = m.Line(
            start=(-v_small * 3.2).tolist(),
            end=(v_small * 3.2).tolist(),
            color=m.YELLOW,
            stroke_width=7.0,
        )
        eigenlines = m.VGroup(line_large, line_small)

        # Matrix readout in a corner.
        mat_label = m.MathTex("A =", font_size=28)
        mat_matrix = m.Matrix([[3, 1], [0, 2]]).scale(0.45)
        mat_matrix.next_to(mat_label, m.RIGHT, buff=0.12)
        mat_tex = m.VGroup(mat_label, mat_matrix)
        mat_tex.to_corner(m.UL, buff=0.4)

        # Labels on each eigenline color-coded to match.
        teal_label = m.MathTex(r"\lambda = 3", font_size=32, color=m.TEAL).to_corner(
            m.UR, buff=0.4
        )
        yellow_label = m.MathTex(r"\lambda = 2", font_size=32, color=m.YELLOW).next_to(
            teal_label, m.DOWN, aligned_edge=m.RIGHT, buff=0.25
        )

        # Reveal.
        self.play(m.Create(plane), run_time=1.2)
        self.play(m.FadeIn(mat_tex), run_time=0.6)
        self.play(m.Create(eigenlines), run_time=1.2)
        self.play(m.FadeIn(teal_label), m.FadeIn(yellow_label), run_time=0.6)

        # The key move: apply MAT to both the plane AND the eigenlines simultaneously.
        # The plane bends. The eigenlines stay on their direction — they just scale.
        self.play(
            m.ApplyMatrix(MAT, plane),
            m.ApplyMatrix(MAT, eigenlines),
            run_time=3.0,
        )

        self.wait(0.5)
