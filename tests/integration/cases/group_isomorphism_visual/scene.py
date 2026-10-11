import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Isomorphism: $C_4 \\cong \\mathbb{Z}/4\\mathbb{Z}$").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        c4 = m.VGroup()
        z4 = m.VGroup()
        c4_positions = []
        z4_positions = []
        for k in range(4):
            angle = k * math.pi / 2
            c4_pos = np.array([1.5 * math.cos(angle) - 3, 1.5 * math.sin(angle), 0])
            z4_pos = np.array([1.5 * math.cos(angle) + 3, 1.5 * math.sin(angle), 0])
            c4_positions.append(c4_pos)
            z4_positions.append(z4_pos)
            c4.add(m.Dot(c4_pos, color=m.YELLOW, radius=0.15))
            c4.add(m.MathTex(f"r^{k}").scale(0.55).next_to(c4_pos, m.UP, buff=0.15))
            z4.add(m.Dot(z4_pos, color=m.BLUE, radius=0.15))
            z4.add(m.MathTex(f"{k}").scale(0.65).next_to(z4_pos, m.UP, buff=0.15))

        self.play(m.FadeIn(c4), m.FadeIn(z4))

        for c, z in zip(c4_positions, z4_positions):
            arrow = m.Arrow(c, z, color=m.GREEN, stroke_width=2, buff=0.3)
            self.play(m.GrowArrow(arrow), run_time=0.3)
        self.wait(1.5)
