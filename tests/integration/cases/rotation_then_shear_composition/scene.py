import math

import numpy as np

import manimgx as m

THETA = math.pi / 4
ROT = np.array(
    [[math.cos(THETA), -math.sin(THETA)], [math.sin(THETA), math.cos(THETA)]]
)
SHEAR = np.array([[1.0, 1.0], [0.0, 1.0]])


def make_plane() -> m.NumberPlane:
    return m.NumberPlane(
        x_range=[-4, 4, 1],
        y_range=[-3, 3, 1],
        x_length=5,
        y_length=4,
        background_line_style={"stroke_color": m.BLUE_D, "stroke_width": 1.5},
    )


class TeacherScene(m.Scene):
    def construct(self) -> None:
        left = make_plane().shift(m.LEFT * 3.4)
        right = make_plane().shift(m.RIGHT * 3.4)
        left_label = (
            m.Tex("Rotate, then shear", color=m.YELLOW)
            .scale(0.65)
            .next_to(
                left,
                m.UP,
                buff=0.15,
            )
        )
        right_label = (
            m.Tex("Shear, then rotate", color=m.RED)
            .scale(0.65)
            .next_to(
                right,
                m.UP,
                buff=0.15,
            )
        )

        self.play(m.Create(left), m.Create(right))
        self.play(m.Write(left_label), m.Write(right_label))
        self.wait(0.4)

        self.play(
            m.ApplyMatrix(ROT.tolist(), left),
            m.ApplyMatrix(SHEAR.tolist(), right),
            run_time=1.4,
        )
        self.wait(0.5)

        self.play(
            m.ApplyMatrix(SHEAR.tolist(), left),
            m.ApplyMatrix(ROT.tolist(), right),
            run_time=1.4,
        )

        caption = (
            m.Tex("Different! Matrix composition isn't commutative.")
            .scale(0.85)
            .to_edge(
                m.DOWN,
                buff=0.4,
            )
        )
        self.play(m.Write(caption))
        self.wait(2.0)
