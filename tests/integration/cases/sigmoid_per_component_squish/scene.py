import math

import manimgx as m

INPUT = [-2.5, -0.5, 1.0, 3.0]


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex(
            "Sigmoid squashes each component into ",
            "$(0, 1)$",
        ).to_edge(m.UP, buff=0.4)
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        input_mat = m.Matrix([[x] for x in INPUT]).scale(0.9).shift(m.LEFT * 4)
        arrow = m.Arrow(m.LEFT * 2.2, m.RIGHT * 0.4, color=m.YELLOW, buff=0)
        sigma = (
            m.MathTex("\\sigma", color=m.YELLOW)
            .scale(1.2)
            .next_to(arrow, m.UP, buff=0.15)
        )
        output_mat = (
            m.Matrix(
                [[f"{sigmoid(x):.2f}"] for x in INPUT],
            )
            .scale(0.9)
            .shift(m.RIGHT * 3)
        )
        output_mat.set_color(m.GREEN)

        self.play(m.Write(input_mat))
        self.play(m.GrowArrow(arrow), m.Write(sigma))
        self.play(m.Write(output_mat))
        self.wait(2.0)
