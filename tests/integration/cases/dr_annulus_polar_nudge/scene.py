"""Why does d/dr of pi*r^2 equal 2*pi*r? Show the nudge geometrically."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        base_radius = 1.8
        center = 1.0 * m.LEFT

        # The disk of area pi*r^2.
        disk = m.Circle(radius=base_radius, color=m.TEAL_E).move_to(center)
        disk.set_fill(m.TEAL_E, opacity=0.75)
        disk.set_stroke(m.WHITE, width=1.5)

        # Radius label with a small marker line.
        radius_line = m.Line(
            center,
            center + np.array([base_radius, 0.0, 0.0]),
            color=m.WHITE,
            stroke_width=3.0,
        )
        r_label = m.MathTex("r", color=m.WHITE).next_to(radius_line, m.DOWN, buff=0.1)

        self.play(m.Create(disk), run_time=1.2)
        self.play(m.Create(radius_line), m.Write(r_label), run_time=0.8)
        self.wait(0.3)

        # The nudge: an annulus of thickness dr that wraps around the disk.
        dr_tracker = m.ValueTracker(0.5)
        dA = m.always_redraw(
            lambda: m.Annulus(
                inner_radius=base_radius,
                outer_radius=base_radius + dr_tracker.get_value(),
                color=m.RED_E,
                fill_opacity=0.7,
                stroke_color=m.WHITE,
                stroke_width=1.0,
            ).move_to(center)
        )

        # The dr bracket sitting on the right side of the disk.
        def dr_brace() -> m.Line:
            r_outer = base_radius + dr_tracker.get_value()
            y = 0.0
            return m.Line(
                center + np.array([base_radius, y + 0.35, 0.0]),
                center + np.array([r_outer, y + 0.35, 0.0]),
                color=m.YELLOW,
                stroke_width=4.0,
            )

        dr_indicator = m.always_redraw(dr_brace)
        dr_label = m.MathTex("dr", color=m.YELLOW).next_to(
            np.array([center[0] + base_radius + 0.3, 0.6, 0.0]),
            m.UP,
            buff=0.1,
        )

        self.add(dA, dr_indicator)
        self.play(m.FadeIn(dA), m.Write(dr_label), run_time=0.8)

        # Equation in the upper right — spelled out next to the picture.
        area_eq = m.MathTex(R"dA = 2 \pi r \cdot dr").scale(1.1).to_edge(m.UP)
        self.play(m.Write(area_eq), run_time=1.2)
        self.wait(0.3)

        # Let the student SEE dr shrink toward the limit.
        self.play(dr_tracker.animate.set_value(0.25), run_time=1.5)
        self.play(dr_tracker.animate.set_value(0.1), run_time=1.5)
        self.play(dr_tracker.animate.set_value(0.05), run_time=1.5)
        self.wait(0.3)

        derivative_eq = (
            m.MathTex(R"\frac{d}{dr}(\pi r^2) = 2 \pi r")
            .scale(1.1)
            .next_to(area_eq, m.DOWN, buff=0.3)
        )
        self.play(m.Write(derivative_eq), run_time=1.2)
        self.wait(0.5)
