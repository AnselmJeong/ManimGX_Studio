import math

import manim as m
import numpy as np

NUM = 12
G = 9.8


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Pendulums of varying lengths").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        t = m.ValueTracker(0.0)

        def make_pendulum(i: int, length: float, pivot: np.ndarray):
            freq = math.sqrt(G / length)

            def bob_pos() -> np.ndarray:
                theta = 0.55 * math.cos(freq * t.get_value())
                return pivot + length * np.array(
                    [math.sin(theta), -math.cos(theta), 0.0]
                )

            return (
                m.always_redraw(
                    lambda: m.Line(pivot, bob_pos(), color=m.WHITE, stroke_width=1.5)
                ),
                m.always_redraw(lambda: m.Dot(bob_pos(), color=m.YELLOW, radius=0.08)),
            )

        for i in range(NUM):
            length = 1.5 + i * 0.15
            pivot = np.array([-5.0 + i * 0.85, 2.5, 0.0])
            rod, dot = make_pendulum(i, length, pivot)
            self.add(rod, dot)

        self.play(t.animate.set_value(14.0), run_time=10.0, rate_func=m.linear)
        self.wait(1.0)
