import math

import numpy as np

import manimgx as m

RADIUS = 2.5
OFFSET = 2.0


def pt_a(t: float) -> np.ndarray:
    return RADIUS * np.array([math.cos(t), math.sin(t), 0.0])


def pt_b(t: float) -> np.ndarray:
    return RADIUS * np.array([math.cos(t + OFFSET), math.sin(t + OFFSET), 0.0])


def midpoint(t: float) -> np.ndarray:
    return (pt_a(t) + pt_b(t)) / 2.0


class TeacherScene(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=RADIUS, color=m.WHITE, stroke_width=2)
        self.add(circle)

        title = (
            m.Tex(
                "Each chord ",
                "$\\leftrightarrow$",
                " its midpoint",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.4)
        )
        self.play(m.Write(title))

        t = m.ValueTracker(0.0)
        dot_a = m.always_redraw(
            lambda: m.Dot(pt_a(t.get_value()), color=m.GREEN, radius=0.1)
        )
        dot_b = m.always_redraw(
            lambda: m.Dot(pt_b(t.get_value()), color=m.RED, radius=0.1)
        )
        chord = m.always_redraw(
            lambda: m.Line(
                pt_a(t.get_value()), pt_b(t.get_value()), color=m.BLUE, stroke_width=2
            )
        )
        mid_dot = m.always_redraw(
            lambda: m.Dot(midpoint(t.get_value()), color=m.YELLOW, radius=0.12)
        )
        trace = m.TracedPath(
            lambda: midpoint(t.get_value()), stroke_color=m.YELLOW, stroke_width=3
        )

        self.add(dot_a, dot_b, chord, mid_dot, trace)
        self.play(t.animate.set_value(2 * math.pi), run_time=6.0, rate_func=m.linear)
        self.wait(1.5)
