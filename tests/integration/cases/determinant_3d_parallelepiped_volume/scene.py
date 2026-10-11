import numpy as np

import manimgx as m

M = np.array(
    [
        [2.0, 0.5, 0.0],
        [0.0, 1.5, 0.5],
        [0.0, 0.0, 1.2],
    ]
)


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-40 * m.DEGREES)

        axes = m.ThreeDAxes(
            x_range=[-1, 4, 1],
            y_range=[-1, 4, 1],
            z_range=[-1, 4, 1],
        )
        self.play(m.Create(axes))

        cube = m.Cube(side_length=1.0, color=m.YELLOW, fill_opacity=0.4, stroke_width=2)
        cube.move_to([0.5, 0.5, 0.5])
        self.play(m.FadeIn(cube))

        vol_label = m.MathTex("V = 1", color=m.YELLOW).to_corner(m.UR, buff=0.5)
        self.add_fixed_in_frame_mobjects(vol_label)
        self.wait(0.5)

        det = abs(float(np.linalg.det(M)))
        new_vol_label = m.MathTex(
            f"V = {det:.2f}",
            color=m.YELLOW,
        ).to_corner(m.UR, buff=0.5)
        self.add_fixed_in_frame_mobjects(new_vol_label)

        self.play(
            m.ApplyMatrix(M.tolist(), cube),
            m.Transform(vol_label, new_vol_label),
            run_time=2.5,
        )

        det_caption = m.MathTex(
            "\\det(M) = ",
            f"{det:.2f}",
        ).to_edge(m.DOWN, buff=0.5)
        det_caption[1].set_color(m.YELLOW)
        self.add_fixed_in_frame_mobjects(det_caption)
        self.wait(2.0)
