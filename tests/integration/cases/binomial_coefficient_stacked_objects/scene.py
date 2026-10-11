import math
from itertools import combinations

import numpy as np

import manimgx as m

N = 5
K = 3
SPACING = 1.1


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.MathTex(
                f"\\binom{{{N}}}{{{K}}} = {math.comb(N, K)}",
            )
            .scale(1.2)
            .to_edge(m.UP, buff=0.4)
        )
        self.play(m.Write(title))

        positions = [
            np.array([(i - (N - 1) / 2.0) * SPACING, 0.0, 0.0]) for i in range(N)
        ]
        objects = m.VGroup(
            *[
                m.Circle(
                    radius=0.3,
                    color=m.GREY,
                    fill_color=m.GREY,
                    fill_opacity=0.3,
                    stroke_width=1.5,
                ).move_to(pos)
                for pos in positions
            ]
        )
        self.play(m.FadeIn(objects))

        for combo in combinations(range(N), K):
            anims: list[m.Animation] = []
            for i in range(N):
                if i in combo:
                    anims.append(
                        objects[i]
                        .animate.set_color(m.YELLOW)
                        .set_fill(m.YELLOW, opacity=0.9),
                    )
                else:
                    anims.append(
                        objects[i]
                        .animate.set_color(m.GREY)
                        .set_fill(m.GREY, opacity=0.3),
                    )
            self.play(*anims, run_time=0.4)
        self.wait(1.0)
