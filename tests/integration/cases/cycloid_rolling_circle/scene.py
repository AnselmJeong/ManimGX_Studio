import math

import numpy as np

import manimgx as m

R = 0.7
GROUND_Y = -2.0
T_END = 4.0 * math.pi


class TeacherScene(m.Scene):
    def construct(self) -> None:
        ground = m.Line(
            m.LEFT * 6 + m.UP * GROUND_Y,
            m.RIGHT * 6 + m.UP * GROUND_Y,
            color=m.WHITE,
            stroke_width=2,
        )
        self.add(ground)

        title = (
            m.Tex(
                "Cycloid: path traced by a point on a rolling circle",
            )
            .scale(0.75)
            .to_edge(m.UP, buff=0.4)
        )
        self.play(m.Write(title))

        t = m.ValueTracker(0.0)

        def get_center() -> np.ndarray:
            return np.array([R * t.get_value() - 3.0, GROUND_Y + R, 0.0])

        def get_marker() -> np.ndarray:
            theta = t.get_value()
            return get_center() + R * np.array(
                [-math.sin(theta), -math.cos(theta), 0.0]
            )

        circle = m.always_redraw(
            lambda: m.Circle(
                radius=R,
                color=m.BLUE,
                stroke_width=2,
            ).move_to(get_center())
        )
        spoke = m.always_redraw(
            lambda: m.Line(get_center(), get_marker(), color=m.BLUE, stroke_width=1.5)
        )
        marker = m.always_redraw(
            lambda: m.Dot(get_marker(), color=m.YELLOW, radius=0.08)
        )
        trace = m.TracedPath(
            get_marker,
            stroke_color=m.YELLOW,
            stroke_width=3,
        )

        self.add(circle, spoke, marker, trace)
        self.wait(0.3)
        self.play(t.animate.set_value(T_END), run_time=6.0, rate_func=m.linear)
        self.wait(1.2)
