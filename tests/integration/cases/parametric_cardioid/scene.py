"""Plot the cardioid r(theta) = 1 - cos(theta) on axes."""

import math

import manimgx as m

# Eval metadata (most evals leave these empty)
EVAL_MUST_NOT_USE: set[str] = {"axes.plot_parametric_curve"}
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        axes = m.Axes(
            x_range=(-2.5, 0.5, 0.5),
            y_range=(-1.5, 1.5, 0.5),
            x_length=9.0,
            y_length=5.0,
        )
        cardioid = m.ParametricFunction(
            lambda t: axes.c2p(
                (1 - math.cos(t)) * math.cos(t) - 1,
                (1 - math.cos(t)) * math.sin(t),
            ),
            t_range=(0.0, 2 * m.PI),
            color=m.TEAL,
        )

        label = m.MathTex(R"r(\theta) = 1 - \cos(\theta)").to_corner(m.UR, buff=0.5)

        self.play(m.Create(axes), run_time=1.5)
        self.play(m.Write(label), run_time=1.0)
        self.play(m.Create(cardioid), run_time=4.0)
        self.wait(0.5)
