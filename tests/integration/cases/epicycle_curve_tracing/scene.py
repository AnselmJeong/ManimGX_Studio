import math

import numpy as np

import manimgx as m

R = [1.4, 0.8, 0.4]
F = [1, 4, -2]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Epicycle curve from 3 rotating vectors")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        t = m.ValueTracker(0.0)

        def chain_pos(up_to: int = 3) -> np.ndarray:
            pos = np.array([0.0, 0.0, 0.0])
            for i in range(up_to):
                angle = F[i] * t.get_value()
                pos += R[i] * np.array([math.cos(angle), math.sin(angle), 0.0])
            return pos

        for i in range(3):
            self.add(
                m.always_redraw(
                    lambda i=i: m.Circle(
                        radius=R[i],
                        color=m.BLUE,
                        stroke_width=1,
                        stroke_opacity=0.4,
                    ).move_to(chain_pos(up_to=i)),
                ),
                m.always_redraw(
                    lambda i=i: m.Line(
                        chain_pos(up_to=i),
                        chain_pos(up_to=i + 1),
                        color=m.YELLOW,
                        stroke_width=2.5,
                    ),
                ),
            )
        trace = m.TracedPath(chain_pos, stroke_color=m.GREEN, stroke_width=2.5)
        self.add(trace)
        self.play(t.animate.set_value(2 * math.pi), run_time=6.0, rate_func=m.linear)
        self.wait(1.5)
