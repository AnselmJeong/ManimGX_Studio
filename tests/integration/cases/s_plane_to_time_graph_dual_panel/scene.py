"""Show what e^(st) looks like for different s. Let me see s = i, s = -0.5, s = -0.3 + i, with the real-part graph next to the s-plane."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        plane = (
            m.ComplexPlane(
                x_range=(-2.0, 2.0, 1.0),
                y_range=(-2.0, 2.0, 1.0),
            )
            .scale(0.6)
            .move_to(3.5 * m.LEFT)
        )

        axes = (
            m.Axes(
                x_range=(0.0, 5.0, 1.0),
                y_range=(-2.0, 2.0, 1.0),
            )
            .scale(0.6)
            .move_to(3.5 * m.RIGHT)
        )

        s_tracker = m.ComplexValueTracker(complex(0.0, 1.0))

        s_dot = m.always_redraw(
            lambda: m.Dot(plane.n2p(s_tracker.get_value()), radius=0.08, color=m.YELLOW)
        )

        def make_curve() -> m.VMobject:
            s_val = s_tracker.get_value()
            return axes.plot(
                lambda t: float(np.exp(s_val * t).real),
                x_range=(0.0, 5.0),
            ).set_stroke(m.TEAL, width=3.0)

        curve = m.always_redraw(make_curve)

        title = m.MathTex(R"e^{st}").scale(1.1).to_edge(m.UP, buff=0.3)

        self.play(
            m.Create(plane),
            m.Create(axes),
            run_time=1.5,
        )
        self.play(m.Write(title), run_time=0.6)
        self.add(s_dot, curve)
        self.wait(0.5)
        self.play(
            s_tracker.animate.set_value(complex(-0.5, 0.0)),
            run_time=2.0,
        )
        self.play(
            s_tracker.animate.set_value(complex(-0.3, 1.0)),
            run_time=2.0,
        )
        self.wait(1.0)
        self.wait(0.5)
