"""Show me how sine and cosine come out of rotating a unit vector."""

import math

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        # A compact unit-circle plane centered a bit left of the origin.
        plane_center = 1.5 * m.LEFT + 0.3 * m.UP
        plane = m.NumberPlane(
            x_range=(-1.2, 1.2, 0.5),
            y_range=(-1.2, 1.2, 0.5),
            x_length=4.0,
            y_length=4.0,
        ).move_to(plane_center)

        # Reference unit circle.
        unit_circle = m.Circle(radius=2.0, color=m.GREY_B, stroke_width=2.0).move_to(
            plane_center
        )

        theta = m.ValueTracker(0.0)
        tip_scale = 2.0  # plane x_length / x_range span = 4 / 2 = 2

        def tip_position() -> np.ndarray:
            ang = theta.get_value()
            return plane_center + tip_scale * np.array(
                [math.cos(ang), math.sin(ang), 0.0]
            )

        # Main rotating unit vector (yellow).
        main_vec = m.always_redraw(
            lambda: m.Arrow(
                plane_center,
                tip_position(),
                color=m.YELLOW,
                buff=0.0,
                stroke_width=6.0,
            )
        )

        # Horizontal cos(theta) component along the x-axis.
        cos_vec = m.always_redraw(
            lambda: m.Arrow(
                plane_center,
                plane_center
                + tip_scale * np.array([math.cos(theta.get_value()), 0.0, 0.0]),
                color=m.RED,
                buff=0.0,
                stroke_width=6.0,
            )
        )

        # Vertical sin(theta) component — perpendicular, starts at the tip of cos.
        sin_vec = m.always_redraw(
            lambda: m.Arrow(
                plane_center
                + tip_scale * np.array([math.cos(theta.get_value()), 0.0, 0.0]),
                tip_position(),
                color=m.GREEN,
                buff=0.0,
                stroke_width=6.0,
            )
        )

        # Arc showing the angle theta from the x-axis.
        theta_arc = m.always_redraw(
            lambda: m.Arc(
                radius=0.5,
                start_angle=0.0,
                angle=max(theta.get_value(), 1e-4),
                color=m.WHITE,
                stroke_width=3.0,
            ).shift(plane_center)
        )
        theta_label = m.MathTex(R"\theta", color=m.WHITE).scale(0.8)
        theta_label.add_updater(
            lambda lab: lab.move_to(
                plane_center
                + 0.8
                * np.array(
                    [
                        math.cos(theta.get_value() / 2),
                        math.sin(theta.get_value() / 2),
                        0.0,
                    ]
                )
            )
        )

        # Legend-style equation at the bottom.
        equation = (
            m.MathTex(R"\vec{v} = \cos\theta \, \hat{x} + \sin\theta \, \hat{y}")
            .scale(0.9)
            .to_edge(m.DOWN)
        )

        # Build the scene.
        self.play(m.Create(plane), m.Create(unit_circle), run_time=1.2)
        self.play(m.Write(equation), run_time=1.0)
        self.add(main_vec, cos_vec, sin_vec, theta_arc, theta_label)
        self.play(
            theta.animate.set_value(2 * m.PI),
            run_time=6.0,
            rate_func=m.linear,
        )
        self.wait(0.5)
