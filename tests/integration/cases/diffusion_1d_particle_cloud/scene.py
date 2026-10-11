import numpy as np

import manimgx as m

N_PARTICLES = 60


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("1D diffusion: particles spread out")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        ax = m.NumberLine(
            x_range=[-5, 5, 1],
            length=11,
            include_numbers=True,
        ).shift(m.DOWN * 0.5)
        self.add(ax)

        rng = np.random.default_rng(42)
        positions = rng.normal(0.0, 0.15, N_PARTICLES)
        dots = [
            m.Dot(ax.n2p(float(p)) + m.UP * 0.05 * (i % 3), color=m.YELLOW, radius=0.06)
            for i, p in enumerate(positions)
        ]
        for d in dots:
            self.add(d)

        for step in range(8):
            anims = []
            for i, d in enumerate(dots):
                jitter = float(rng.normal(0.0, 0.3))
                positions[i] += jitter
                new_pt = ax.n2p(float(positions[i])) + m.UP * 0.05 * (i % 3)
                anims.append(d.animate.move_to(new_pt))
            self.play(*anims, run_time=0.45)
        self.wait(1.5)
