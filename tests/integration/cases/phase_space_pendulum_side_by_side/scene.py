"""Explain phase space using a pendulum: show the real pendulum swinging next to a dot tracing its (theta, theta-dot) state."""

import math

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


# Closed-form, damped pendulum angle — keeps the sim deterministic and cheap.
def theta(s: float) -> float:
    return 0.7 * math.cos(s) * math.exp(-0.05 * s)


def theta_dot(s: float, h: float = 0.01) -> float:
    return (theta(s + h) - theta(s - h)) / (2 * h)


class TeacherScene(m.Scene):
    def construct(self):
        t = m.ValueTracker(0.0)

        # LEFT: real pendulum.
        pivot = 3.2 * m.LEFT + 2.2 * m.UP
        rod_length = 2.0

        def bob_position() -> np.ndarray:
            ang = theta(t.get_value())
            return pivot + rod_length * np.array([math.sin(ang), -math.cos(ang), 0.0])

        pivot_dot = m.Dot(pivot, color=m.WHITE, radius=0.06)
        rod = m.always_redraw(
            lambda: m.Line(pivot, bob_position(), color=m.WHITE, stroke_width=4.0)
        )
        bob = m.always_redraw(
            lambda: m.Dot(bob_position(), color=m.YELLOW, radius=0.16)
        )
        pendulum_label = m.Text("Pendulum", font_size=28).move_to(
            pivot + np.array([0.0, 0.5, 0.0])
        )

        # RIGHT: phase plane.
        plane_center = 3.2 * m.RIGHT + 0.2 * m.DOWN
        plane = m.NumberPlane(
            x_range=(-1.0, 1.0, 0.5),
            y_range=(-1.0, 1.0, 0.5),
            x_length=4.0,
            y_length=4.0,
        ).move_to(plane_center)

        x_axis_label = m.MathTex(R"\theta", color=m.YELLOW).next_to(
            plane, m.RIGHT, buff=0.1
        )
        y_axis_label = m.MathTex(R"\dot\theta", color=m.GREEN).next_to(
            plane, m.UP, buff=0.1
        )
        phase_title = m.Text("Phase space", font_size=28).next_to(
            plane, m.DOWN, buff=0.25
        )

        def state_point() -> np.ndarray:
            s = t.get_value()
            return plane_center + np.array([theta(s), theta_dot(s), 0.0])

        state_dot = m.always_redraw(
            lambda: m.Dot(state_point(), color=m.RED, radius=0.09)
        )
        trace = m.TracedPath(state_dot.get_center, stroke_color=m.RED, stroke_width=3.0)

        # Build the scene.
        self.play(
            m.Create(plane),
            m.Write(pendulum_label),
            m.Write(phase_title),
            m.Write(x_axis_label),
            m.Write(y_axis_label),
            run_time=1.5,
        )
        self.add(pivot_dot, rod, bob, state_dot, trace)
        self.play(m.FadeIn(pivot_dot), run_time=0.3)
        self.play(
            t.animate.set_value(12.0),
            run_time=6.0,
            rate_func=m.linear,
        )
        self.wait(0.5)
