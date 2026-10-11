import math

import numpy as np

import manimgx as m

SOURCE = np.array([-4.5, 0.0, 0.0])
SCREEN_CENTER = np.array([2.5, 0.0, 0.0])
SCREEN_HALF = 1.5


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Light from a source, screen at varying angle",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        source = m.Dot(SOURCE, color=m.YELLOW, radius=0.15)
        source_label = (
            m.Tex("source", color=m.YELLOW).scale(0.6).next_to(source, m.UP, buff=0.15)
        )
        self.play(m.FadeIn(source), m.Write(source_label))

        theta = m.ValueTracker(0.0)

        def screen() -> m.Line:
            angle = theta.get_value() + math.pi / 2
            dir_vec = np.array([math.cos(angle), math.sin(angle), 0.0])
            return m.Line(
                SCREEN_CENTER - SCREEN_HALF * dir_vec,
                SCREEN_CENTER + SCREEN_HALF * dir_vec,
                color=m.BLUE,
                stroke_width=4,
            )

        def rays() -> m.VGroup:
            angle = theta.get_value() + math.pi / 2
            dir_vec = np.array([math.cos(angle), math.sin(angle), 0.0])
            grp = m.VGroup()
            for t_along in np.linspace(0.0, 1.0, 8):
                hit = SCREEN_CENTER + (2 * t_along - 1) * SCREEN_HALF * dir_vec
                grp.add(
                    m.Line(
                        SOURCE,
                        hit,
                        color=m.YELLOW,
                        stroke_width=1,
                        stroke_opacity=0.55,
                    ),
                )
            return grp

        self.add(m.always_redraw(screen), m.always_redraw(rays))
        self.play(theta.animate.set_value(math.pi / 3), run_time=2.5)
        self.play(theta.animate.set_value(-math.pi / 3), run_time=2.5)
        self.wait(1.0)
