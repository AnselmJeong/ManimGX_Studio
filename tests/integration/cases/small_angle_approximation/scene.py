"""Why is sin(theta) approx theta for small angles? Show on a unit circle."""

import math

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        # A compact plane spanning [-0.3, 1.3] in both axes, scaled up.
        plane = m.NumberPlane(
            x_range=(-0.3, 1.3, 0.5),
            y_range=(-0.3, 1.3, 0.5),
            x_length=4.2,
            y_length=4.2,
        )
        plane.shift(1.5 * m.LEFT + 0.2 * m.DOWN)
        # manimgx Axes/NumberPlane don't expose .x_axis directly — compute the
        # world-space size of one plane unit by measuring c2p deltas.
        origin = plane.c2p(0.0, 0.0)
        unit = float(plane.c2p(1.0, 0.0)[0] - origin[0])

        # Unit circle with radius = one plane-unit.
        unit_circle = m.Circle(radius=unit, color=m.GREY_B, stroke_width=2.5)
        unit_circle.move_to(origin)

        # Angle tracker — starts at 45 degrees.
        theta = m.ValueTracker(45.0 * m.DEGREES)

        # Dot on circle at (cos theta, sin theta).
        dot = m.always_redraw(
            lambda: m.Dot(
                plane.c2p(
                    math.cos(theta.get_value()),
                    math.sin(theta.get_value()),
                ),
                color=m.YELLOW,
                radius=0.08,
            )
        )

        # Blue radius from origin to dot, labeled "1".
        radius_line = m.always_redraw(
            lambda: m.Line(
                origin,
                plane.c2p(
                    math.cos(theta.get_value()),
                    math.sin(theta.get_value()),
                ),
                color=m.BLUE,
                stroke_width=4.0,
            )
        )
        radius_label = m.MathTex("1", color=m.BLUE).scale(0.7)
        radius_label.add_updater(
            lambda lab: lab.move_to(
                origin
                + 0.6
                * unit
                * np.array(
                    [
                        math.cos(theta.get_value() + math.pi / 2) * 0.25
                        + math.cos(theta.get_value()),
                        math.sin(theta.get_value() + math.pi / 2) * 0.25
                        + math.sin(theta.get_value()),
                        0.0,
                    ]
                )
            )
        )

        # Red horizontal line from origin to (cos theta, 0), labeled "cos theta".
        cos_line = m.always_redraw(
            lambda: m.Line(
                origin,
                plane.c2p(math.cos(theta.get_value()), 0.0),
                color=m.RED,
                stroke_width=4.0,
            )
        )
        cos_label = m.MathTex(R"\cos\theta", color=m.RED).scale(0.6)
        cos_label.add_updater(
            lambda lab: lab.next_to(
                plane.c2p(math.cos(theta.get_value()) * 0.5, 0.0),
                m.DOWN,
                buff=0.1,
            )
        )

        # Green vertical line from (cos theta, 0) to (cos theta, sin theta), labeled "sin theta".
        sin_line = m.always_redraw(
            lambda: m.Line(
                plane.c2p(math.cos(theta.get_value()), 0.0),
                plane.c2p(
                    math.cos(theta.get_value()),
                    math.sin(theta.get_value()),
                ),
                color=m.GREEN,
                stroke_width=4.0,
            )
        )
        sin_label = m.MathTex(R"\sin\theta", color=m.GREEN).scale(0.6)
        sin_label.add_updater(
            lambda lab: lab.next_to(
                plane.c2p(
                    math.cos(theta.get_value()),
                    math.sin(theta.get_value()) * 0.5,
                ),
                m.RIGHT,
                buff=0.1,
            )
        )

        # Small arc showing theta at the origin.
        arc_theta = m.always_redraw(
            lambda: m.Arc(
                start_angle=0.0,
                angle=max(theta.get_value(), 1e-3),
                radius=0.4,
                color=m.YELLOW,
                stroke_width=3.0,
            ).shift(origin)
        )
        theta_label = m.MathTex(R"\theta", color=m.YELLOW).scale(0.7)
        theta_label.add_updater(
            lambda lab: lab.move_to(
                origin
                + 0.6
                * np.array(
                    [
                        math.cos(theta.get_value() / 2),
                        math.sin(theta.get_value() / 2),
                        0.0,
                    ]
                )
            )
        )

        # Caption in the corner: sin theta approx theta for small theta.
        caption = (
            m.MathTex(R"\sin\theta \approx \theta \text{ for small } \theta")
            .scale(0.75)
            .to_corner(m.UR, buff=0.4)
        )

        # --- Build the scene ---
        self.play(m.Create(plane), run_time=0.8)
        self.play(m.Create(unit_circle), run_time=1.0)
        self.add(radius_line, radius_label, arc_theta, theta_label, dot)
        self.play(m.Write(caption), run_time=1.0)
        self.add(cos_line, cos_label, sin_line, sin_label)
        self.wait(0.5)

        # Sweep theta from 45 degrees down to 5 degrees — watch sin theta approach the arc length.
        self.play(
            theta.animate.set_value(5.0 * m.DEGREES),
            run_time=4.0,
            rate_func=m.smooth,
        )
        self.wait(0.5)
