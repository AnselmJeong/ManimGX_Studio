import math

import numpy as np

import manimgx as m

L = 2.0
G = 9.8
THETA0 = math.pi / 3
OMEGA = math.sqrt(G / L)


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Pendulum and its $\\theta(t)$ curve").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        pivot = np.array([-3.8, 1.5, 0.0])
        t = m.ValueTracker(0.0)

        def theta_of(tv: float) -> float:
            return THETA0 * math.cos(OMEGA * tv)

        def bob_pos() -> np.ndarray:
            theta = theta_of(t.get_value())
            return pivot + L * np.array([math.sin(theta), -math.cos(theta), 0.0])

        rod = m.always_redraw(
            lambda: m.Line(pivot, bob_pos(), color=m.WHITE, stroke_width=2.5)
        )
        bob = m.always_redraw(lambda: m.Dot(bob_pos(), color=m.YELLOW, radius=0.18))

        ax = m.Axes(
            x_range=[0, 8, 1],
            y_range=[-1.3, 1.3, 0.5],
            x_length=6,
            y_length=3.5,
        ).shift(m.RIGHT * 2.5 + m.DOWN * 0.2)
        self.add(ax)

        graph = m.always_redraw(
            lambda: ax.plot(
                theta_of,
                color=m.YELLOW,
                x_range=[0.0, max(0.01, t.get_value())],
            ),
        )

        self.add(rod, bob, graph)
        self.play(t.animate.set_value(7.5), run_time=8.0, rate_func=m.linear)
        self.wait(1.0)
