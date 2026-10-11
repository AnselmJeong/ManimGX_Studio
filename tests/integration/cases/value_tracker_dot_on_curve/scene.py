"""Show me a dot sliding along y = sin(x) from x = 0 to x = 2π."""

import math

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self):
        axes = m.Axes(
            x_range=(0.0, 2 * m.PI, m.PI / 2),
            y_range=(-1.2, 1.2, 0.5),
            x_length=10.0,
            y_length=4.0,
        )
        curve = axes.plot(math.sin, x_range=(0.0, 2 * m.PI), color=m.BLUE)

        t = m.ValueTracker(0.0)
        dot = m.always_redraw(
            lambda: m.Dot(
                axes.c2p(t.get_value(), math.sin(t.get_value())),
                color=m.YELLOW,
                radius=0.1,
            )
        )

        self.play(m.Create(axes), run_time=1.0)
        self.play(m.Create(curve), run_time=1.5)
        self.add(dot)
        self.play(
            t.animate.set_value(2 * m.PI),
            run_time=3.0,
            rate_func=m.linear,
        )
        self.wait(0.5)
