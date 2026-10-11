import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Dart throws on a target").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        rings = m.VGroup(
            *[
                m.Circle(
                    radius=r, color=c, fill_color=c, fill_opacity=0.3, stroke_width=2
                )
                for r, c in [
                    (2.5, m.WHITE),
                    (2.0, m.BLUE),
                    (1.5, m.GREEN),
                    (1.0, m.YELLOW),
                    (0.5, m.RED),
                ]
            ]
        )
        self.add(rings)

        rng = np.random.default_rng(42)
        for _ in range(10):
            x = rng.normal(0, 1.1)
            y = rng.normal(0, 1.1)
            dart = m.Dot(np.array([x, y, 0]), color=m.YELLOW, radius=0.1)
            self.play(m.FadeIn(dart, scale=0.3), run_time=0.3)
        self.wait(2.0)
