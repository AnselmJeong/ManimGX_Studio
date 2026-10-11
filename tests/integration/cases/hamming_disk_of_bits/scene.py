import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Disk of bits (Hamming layout)").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        rng = np.random.default_rng(42)
        bits = m.VGroup()
        for ring in range(8):
            r = 0.5 + ring * 0.32
            for i in range(16):
                theta = i * 2 * math.pi / 16
                pos = np.array([r * math.cos(theta), r * math.sin(theta), 0.0])
                val = int(rng.integers(0, 2))
                color = m.WHITE if val == 0 else m.YELLOW
                bits.add(m.Dot(pos, color=color, radius=0.07))
        self.play(m.FadeIn(bits), run_time=2.0)
        self.wait(2.0)
