"""As a dot circles the origin at unit radius, trace out the sine wave it draws on the right."""

import math

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self):
        circle = m.Circle(radius=1.0, color=m.BLUE).move_to(3.5 * m.LEFT)
        axes = m.Axes(
            x_range=(0.0, 2 * m.PI, m.PI / 2),
            y_range=(-1.2, 1.2, 0.5),
            x_length=5.5,
            y_length=2.5,
        ).move_to(2.0 * m.RIGHT)

        t = m.ValueTracker(0.0)

        left_dot = m.Dot(color=m.YELLOW, radius=0.1)
        left_dot.add_updater(
            lambda d: d.move_to(
                circle.point_from_proportion((t.get_value() / (2 * m.PI)) % 1.0)
            )
        )

        right_dot = m.Dot(color=m.YELLOW, radius=0.1)
        right_dot.add_updater(
            lambda d: d.move_to(axes.c2p(t.get_value(), math.sin(t.get_value())))
        )

        trace = m.TracedPath(
            right_dot.get_center, stroke_color=m.BLUE, stroke_width=3.0
        )

        self.play(m.Create(circle), run_time=1.0)
        self.play(m.Create(axes), run_time=1.0)
        self.add(left_dot, right_dot, trace)
        self.play(
            t.animate.set_value(2 * m.PI),
            run_time=4.0,
            rate_func=m.linear,
        )
        self.wait(0.5)
