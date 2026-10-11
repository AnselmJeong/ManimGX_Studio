import numpy as np

import manimgx as m

TERMS = 8


def zeta_warp(p: np.ndarray) -> np.ndarray:
    s_shifted = complex(p[0], p[1]) + 2.5
    total = 0.0 + 0.0j
    for n in range(1, TERMS + 1):
        total += 1.0 / (n**s_shifted)
    return np.array([total.real, total.imag, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.ComplexPlane(
            x_range=[-2, 2, 1],
            y_range=[-2, 2, 1],
            x_length=8,
            y_length=8,
        )
        self.play(m.Create(plane), run_time=1.0)

        title = m.Tex(
            "Riemann ",
            "$\\zeta$",
            " on a shifted half-plane",
        ).to_edge(m.UP, buff=0.4)
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        self.play(plane.animate.apply_function(zeta_warp), run_time=4.0)
        self.wait(2.0)
