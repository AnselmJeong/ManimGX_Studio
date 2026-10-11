import math

import numpy as np

import manimgx as m

N_TERMS = 5
TERMS = [(2 * k + 1, 1.4 / (2 * k + 1)) for k in range(N_TERMS)]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Rotating vectors trace a curve").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        anchor = np.array([-4.0, 0.0, 0.0])
        t = m.ValueTracker(0.0)

        def chain_pos(up_to: int = N_TERMS) -> np.ndarray:
            pos = anchor.copy()
            for i in range(up_to):
                freq, r = TERMS[i]
                angle = freq * t.get_value()
                pos += r * np.array([math.cos(angle), math.sin(angle), 0.0])
            return pos

        for i in range(N_TERMS):
            self.add(
                m.always_redraw(
                    lambda i=i: m.Circle(
                        radius=TERMS[i][1],
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

        trace = m.TracedPath(chain_pos, stroke_color=m.GREEN, stroke_width=3)
        self.add(trace)

        self.play(t.animate.set_value(2 * math.pi), run_time=6.0, rate_func=m.linear)
        self.wait(1.5)
