import math

import numpy as np

import manimgx as m

R1 = 1.5
R2 = 0.8
F1 = 1
F2 = 3


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Two rotating vectors trace an epicycle")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        t = m.ValueTracker(0.0)

        def pos1() -> np.ndarray:
            return np.array(
                [
                    R1 * math.cos(F1 * t.get_value()),
                    R1 * math.sin(F1 * t.get_value()),
                    0.0,
                ]
            )

        def pos2() -> np.ndarray:
            return pos1() + np.array(
                [
                    R2 * math.cos(F2 * t.get_value()),
                    R2 * math.sin(F2 * t.get_value()),
                    0.0,
                ]
            )

        c1 = m.Circle(radius=R1, color=m.BLUE, stroke_width=1.5, stroke_opacity=0.5)
        c2 = m.always_redraw(
            lambda: m.Circle(
                radius=R2,
                color=m.BLUE,
                stroke_width=1.5,
                stroke_opacity=0.5,
            ).move_to(pos1()),
        )
        v1 = m.always_redraw(
            lambda: m.Line(
                np.array([0.0, 0.0, 0.0]), pos1(), color=m.YELLOW, stroke_width=2.5
            ),
        )
        v2 = m.always_redraw(
            lambda: m.Line(pos1(), pos2(), color=m.RED, stroke_width=2.5),
        )
        dot = m.always_redraw(lambda: m.Dot(pos2(), color=m.GREEN, radius=0.1))
        trace = m.TracedPath(pos2, stroke_color=m.GREEN, stroke_width=2.5)

        self.add(c1, c2, v1, v2, dot, trace)
        self.play(t.animate.set_value(2 * math.pi), run_time=6.0, rate_func=m.linear)
        self.wait(1.5)
