import numpy as np

import manimgx as m

# Try [[1, 1], [0, 1]] (shear), [[0, -1], [1, 0]] (90 deg rotation),
# [[2, 0], [0, 2]] (uniform 2x), [[1, 0.5], [0.5, 1]] (symmetric shear).
MATRIX = np.array([[1.0, 1.5], [-0.5, 1.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        background = m.NumberPlane().set_color(m.GREY).set_stroke(opacity=0.25)
        plane = m.NumberPlane(
            background_line_style={"stroke_color": m.BLUE_D, "stroke_width": 2},
        )

        i_hat = m.Arrow(
            m.ORIGIN,
            m.RIGHT,
            buff=0,
            color=m.GREEN,
            stroke_width=6,
            max_tip_length_to_length_ratio=0.2,
        )
        j_hat = m.Arrow(
            m.ORIGIN,
            m.UP,
            buff=0,
            color=m.RED,
            stroke_width=6,
            max_tip_length_to_length_ratio=0.2,
        )

        matrix_str = [[f"{x:.1f}" for x in row] for row in MATRIX]
        matrix_label = m.Matrix(matrix_str).scale(0.7).to_corner(m.UL, buff=0.35)
        matrix_bg = m.BackgroundRectangle(
            matrix_label, color=m.BLACK, fill_opacity=0.75, buff=0.12
        )

        self.add(background)
        self.play(m.Create(plane), run_time=1.0)
        self.play(m.GrowArrow(i_hat), m.GrowArrow(j_hat), run_time=0.6)
        self.play(m.FadeIn(matrix_bg), m.FadeIn(matrix_label))
        self.wait(0.4)

        new_i = MATRIX @ np.array([1.0, 0.0])
        new_j = MATRIX @ np.array([0.0, 1.0])
        new_i_end = np.array([new_i[0], new_i[1], 0.0])
        new_j_end = np.array([new_j[0], new_j[1], 0.0])

        self.play(
            m.ApplyMatrix(MATRIX.tolist(), plane),
            i_hat.animate.put_start_and_end_on(m.ORIGIN, new_i_end),
            j_hat.animate.put_start_and_end_on(m.ORIGIN, new_j_end),
            run_time=2.4,
        )
        self.wait(1.5)
