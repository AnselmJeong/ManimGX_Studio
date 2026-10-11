"""Show Snell's law: a beam hits a glass surface, the refracted angle changes as I sweep the incident angle."""

import math

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Tests ValueTracker driving two Lines + two always_redraw Arcs via a single "
    "theta1 tracker, with theta2 computed live from Snell's law."
)


class TeacherScene(m.Scene):
    def construct(self):
        # Two media: air on top (no fill), glass on bottom (blue, semi-transparent).
        air = (
            m.Rectangle(width=12.0, height=3.2)
            .set_fill(m.BLACK, 0.0)
            .set_stroke(m.WHITE, 1.0)
        )
        air.move_to(1.6 * m.UP)
        glass = (
            m.Rectangle(width=12.0, height=3.2)
            .set_fill(m.BLUE, 0.3)
            .set_stroke(m.BLUE_E, 1.0)
        )
        glass.move_to(1.6 * m.DOWN)

        # Interface line (y = 0).
        interface = m.Line(
            np.array([-6.0, 0.0, 0.0]),
            np.array([6.0, 0.0, 0.0]),
            color=m.WHITE,
            stroke_width=2.5,
        )
        # Normal (dashed vertical through origin).
        normal = m.DashedLine(
            np.array([0.0, -3.1, 0.0]),
            np.array([0.0, 3.1, 0.0]),
            dash_length=0.12,
            color=m.GREY_B,
            stroke_width=1.5,
        )

        air_label = m.Text("air  (n = 1)", font_size=26).move_to(
            np.array([4.2, 2.8, 0.0])
        )
        glass_label = m.Text("glass  (n = 1.5)", font_size=26).move_to(
            np.array([4.0, -2.8, 0.0])
        )

        self.play(m.FadeIn(air), m.FadeIn(glass), run_time=0.8)
        self.play(m.Create(interface), m.Create(normal), run_time=0.8)
        self.play(m.Write(air_label), m.Write(glass_label), run_time=0.8)

        # Snell setup.
        n_glass = 1.5
        beam_len = 3.0
        arc_radius = 0.8
        theta1 = m.ValueTracker(40.0 * m.DEGREES)
        origin = np.array([0.0, 0.0, 0.0])

        def compute_theta2() -> float:
            # sin(theta1) = n * sin(theta2); n > 1 keeps the asin safe.
            s = math.sin(theta1.get_value()) / n_glass
            s = max(-1.0, min(1.0, s))
            return math.asin(s)

        # Incident beam: enters from upper-left of the normal at angle theta1.
        incident = m.always_redraw(
            lambda: m.Line(
                origin
                + beam_len
                * np.array(
                    [
                        -math.sin(theta1.get_value()),
                        math.cos(theta1.get_value()),
                        0.0,
                    ]
                ),
                origin,
                color=m.YELLOW,
                stroke_width=4.0,
            )
        )

        # Refracted beam: exits into glass at angle theta2 on the same side (right of normal).
        refracted = m.always_redraw(
            lambda: m.Line(
                origin,
                origin
                + beam_len
                * np.array(
                    [
                        math.sin(compute_theta2()),
                        -math.cos(compute_theta2()),
                        0.0,
                    ]
                ),
                color=m.ORANGE,
                stroke_width=4.0,
            )
        )

        # Arc for theta_1: from upward normal (+y, angle=pi/2) CCW to the incident beam.
        # The incident beam (from origin) goes to (-sin t, cos t), which is at polar angle pi/2 + t.
        theta1_arc = m.always_redraw(
            lambda: m.Arc(
                radius=arc_radius,
                start_angle=math.pi / 2.0,
                angle=theta1.get_value(),
                color=m.YELLOW,
                stroke_width=3.0,
            ).shift(origin)
        )

        # Arc for theta_2: from downward normal (-y, angle=-pi/2) CCW to the refracted beam.
        # Refracted beam direction is (sin t2, -cos t2), at polar angle -pi/2 + t2.
        theta2_arc = m.always_redraw(
            lambda: m.Arc(
                radius=arc_radius,
                start_angle=-math.pi / 2.0,
                angle=compute_theta2(),
                color=m.ORANGE,
                stroke_width=3.0,
            ).shift(origin)
        )

        # Labels positioned at the midangle of each arc.
        theta1_label = m.MathTex(R"\theta_1", color=m.YELLOW).scale(0.9)
        theta1_label.add_updater(
            lambda lab: lab.move_to(
                origin
                + (arc_radius + 0.35)
                * np.array(
                    [
                        -math.sin(theta1.get_value() / 2.0),
                        math.cos(theta1.get_value() / 2.0),
                        0.0,
                    ]
                )
            )
        )

        theta2_label = m.MathTex(R"\theta_2", color=m.ORANGE).scale(0.9)
        theta2_label.add_updater(
            lambda lab: lab.move_to(
                origin
                + (arc_radius + 0.35)
                * np.array(
                    [
                        math.sin(compute_theta2() / 2.0),
                        -math.cos(compute_theta2() / 2.0),
                        0.0,
                    ]
                )
            )
        )

        formula = m.MathTex(R"\sin\theta_1 = n\,\sin\theta_2", font_size=36).to_corner(
            m.UL, buff=0.4
        )

        self.play(m.Write(formula), run_time=0.8)
        self.add(
            incident, refracted, theta1_arc, theta2_arc, theta1_label, theta2_label
        )
        self.wait(0.3)

        # Sweep theta1 up to 70° and back down to 20°.
        self.play(
            theta1.animate.set_value(70.0 * m.DEGREES),
            run_time=3.0,
            rate_func=m.linear,
        )
        self.play(
            theta1.animate.set_value(20.0 * m.DEGREES),
            run_time=2.5,
            rate_func=m.linear,
        )

        self.wait(0.5)
