"""Why do closer stars shift more in the sky than distant stars as Earth orbits? Show the parallax angle."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        # Earth on the left — small blue filled circle.
        earth_center = 4.0 * m.LEFT
        earth_radius = 0.5
        earth = m.Circle(radius=earth_radius, color=m.BLUE_E)
        earth.set_fill(m.BLUE_E, opacity=0.5)
        earth.set_stroke(m.WHITE, width=2.0)
        earth.move_to(earth_center)
        earth_label = (
            m.MathTex(R"\text{Earth}").scale(0.55).next_to(earth, m.LEFT, buff=0.2)
        )

        # Two observer dots on the surface — top and bottom of Earth.
        obs_top_point = earth_center + np.array([0.0, earth_radius, 0.0])
        obs_bot_point = earth_center + np.array([0.0, -earth_radius, 0.0])
        obs_top = m.Dot(obs_top_point, color=m.YELLOW, radius=0.08)
        obs_bot = m.Dot(obs_bot_point, color=m.RED, radius=0.08)

        # Distant star — a yellow dot on the right.
        star_point = 4.5 * m.RIGHT
        star = m.Dot(star_point, radius=0.1, color=m.YELLOW)
        star_label = (
            m.MathTex(R"\text{star}").scale(0.55).next_to(star, m.RIGHT, buff=0.2)
        )

        # Two dashed sight-lines from the observers to the star.
        sight_top = m.DashedLine(
            obs_top_point, star_point, color=m.WHITE, stroke_width=2.0
        )
        sight_bot = m.DashedLine(
            obs_bot_point, star_point, color=m.WHITE, stroke_width=2.0
        )

        # Baseline between the two observers + a brace labeled "baseline".
        baseline = m.Line(
            obs_top_point, obs_bot_point, color=m.YELLOW, stroke_width=4.0
        )
        baseline_brace = m.Brace(baseline, direction=m.LEFT, buff=0.1)
        baseline_text = baseline_brace.get_text("baseline")
        baseline_text.scale(0.7)

        # Parallax angle arc near the star.
        # Angles from star back to each observer.
        vec_to_top = obs_top_point - star_point
        vec_to_bot = obs_bot_point - star_point
        angle_top = np.arctan2(vec_to_top[1], vec_to_top[0])
        angle_bot = np.arctan2(vec_to_bot[1], vec_to_bot[0])
        parallax_arc = m.Arc(
            start_angle=angle_bot,
            angle=angle_top - angle_bot,
            radius=0.8,
            color=m.TEAL,
            stroke_width=3.0,
        ).shift(star_point)
        theta_label = m.MathTex(R"\theta", color=m.TEAL).scale(0.9)
        theta_label.next_to(parallax_arc, m.LEFT, buff=0.1)

        # Distance formula caption near the bottom.
        formula = (
            m.MathTex(R"\text{distance} \approx \frac{\text{baseline}}{\theta}")
            .scale(0.8)
            .to_edge(m.DOWN, buff=0.4)
        )

        # --- Build the scene, revealing elements in pedagogical order. ---

        # 1. Earth.
        self.play(m.Create(earth), m.Write(earth_label), run_time=1.0)

        # 2. Two observers on Earth's surface.
        self.play(
            m.Create(obs_top),
            m.Create(obs_bot),
            run_time=0.8,
        )

        # 3. Distant star on the right.
        self.play(m.Create(star), m.Write(star_label), run_time=0.8)

        # 4. Dashed sight-lines from each observer to the star.
        self.play(
            m.Create(sight_top),
            m.Create(sight_bot),
            run_time=1.5,
        )

        # 5. Baseline between the observers + brace labeled "baseline".
        self.play(m.Create(baseline), run_time=0.6)
        self.play(
            m.Create(baseline_brace),
            m.Write(baseline_text),
            run_time=1.0,
        )

        # 6. Small arc showing the parallax angle theta at the star.
        self.play(m.Create(parallax_arc), m.Write(theta_label), run_time=1.0)

        # 7. The distance formula at the bottom.
        self.play(m.Write(formula), run_time=1.5)

        self.wait(0.5)
