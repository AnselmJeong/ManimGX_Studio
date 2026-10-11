import numpy as np

import manimgx as m

IMAGE = np.array(
    [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0],
    ]
)
KERNEL = np.array(
    [
        [-1, 0, 1],
        [-2, 0, 2],
        [-1, 0, 1],
    ]
)
CELL = 0.55


class TeacherScene(m.Scene):
    def construct(self) -> None:
        image_grp = m.VGroup()
        for i in range(5):
            for j in range(5):
                val = IMAGE[i, j]
                color = m.WHITE if val == 1 else m.DARK_GRAY
                square = m.Square(
                    side_length=CELL,
                    color=m.GREY,
                    fill_color=color,
                    fill_opacity=0.85,
                    stroke_width=1,
                ).move_to([(j - 2) * CELL - 3.0, (2 - i) * CELL, 0])
                image_grp.add(square)
        image_label = m.Tex("input").scale(0.6).next_to(image_grp, m.UP, buff=0.3)

        kernel_grp = m.VGroup()
        for i in range(3):
            for j in range(3):
                val = int(KERNEL[i, j])
                color = m.RED if val < 0 else (m.GREEN if val > 0 else m.GREY)
                square = m.Square(
                    side_length=CELL * 0.9,
                    color=color,
                    fill_color=color,
                    fill_opacity=0.45,
                    stroke_width=1.5,
                ).move_to([(j - 1) * CELL + 1.5, (1 - i) * CELL, 0])
                num = (
                    m.MathTex(str(val), color=m.WHITE)
                    .scale(0.55)
                    .move_to(
                        square.get_center(),
                    )
                )
                kernel_grp.add(square, num)
        kernel_label = (
            m.Tex("Sobel kernel").scale(0.6).next_to(kernel_grp, m.UP, buff=0.3)
        )

        self.play(m.Create(image_grp), m.Write(image_label))
        self.play(m.FadeIn(kernel_grp), m.Write(kernel_label))

        center_val = int(np.sum(KERNEL * IMAGE[1:4, 1:4]))
        result = m.MathTex(
            "\\text{output} = \\sum k_{ij} \\cdot x_{ij} = ",
            str(center_val),
        ).to_edge(m.DOWN, buff=0.5)
        result[1].set_color(m.YELLOW)
        self.play(m.Write(result))
        self.wait(2.0)
