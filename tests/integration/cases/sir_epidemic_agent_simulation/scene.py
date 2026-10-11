import numpy as np

import manimgx as m

GRID_N = 15


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("SIR epidemic spread").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        dots: list[m.Dot] = []
        positions: list[np.ndarray] = []
        for i in range(GRID_N):
            for j in range(GRID_N):
                pos = np.array([-3.5 + j * 0.5, -3.0 + i * 0.4, 0.0])
                positions.append(pos)
                dots.append(m.Dot(pos, color=m.WHITE, radius=0.08))
        for d in dots:
            self.add(d)

        center_idx = GRID_N * GRID_N // 2 + GRID_N // 2
        self.play(dots[center_idx].animate.set_color(m.RED))

        infected = {center_idx}
        for _ in range(5):
            new_infected: set[int] = set()
            for idx in infected:
                p = positions[idx]
                for i, q in enumerate(positions):
                    if i not in infected and np.linalg.norm(q - p) < 0.6:
                        new_infected.add(i)
            if not new_infected:
                break
            self.play(
                *[dots[i].animate.set_color(m.RED) for i in new_infected],
                run_time=0.5,
            )
            infected.update(new_infected)
        self.wait(1.0)
