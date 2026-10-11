import math

import numpy as np

import manimgx as m

L1 = 1.7
L2 = 1.3


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Double pendulum").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        pivot = np.array([0.0, 2.6, 0.0])
        t = m.ValueTracker(0.0)

        def joint_pos() -> np.ndarray:
            theta1 = (math.pi / 3) * math.cos(t.get_value() * 1.4)
            return pivot + L1 * np.array([math.sin(theta1), -math.cos(theta1), 0.0])

        def end_pos() -> np.ndarray:
            theta2 = (math.pi / 2) * math.cos(t.get_value() * 2.3 + 0.5)
            j = joint_pos()
            return j + L2 * np.array([math.sin(theta2), -math.cos(theta2), 0.0])

        rod1 = m.always_redraw(
            lambda: m.Line(pivot, joint_pos(), color=m.WHITE, stroke_width=2.5)
        )
        rod2 = m.always_redraw(
            lambda: m.Line(joint_pos(), end_pos(), color=m.WHITE, stroke_width=2.5)
        )
        joint_dot = m.always_redraw(
            lambda: m.Dot(joint_pos(), color=m.BLUE, radius=0.13)
        )
        end_dot = m.always_redraw(lambda: m.Dot(end_pos(), color=m.YELLOW, radius=0.16))
        trace = m.TracedPath(end_pos, stroke_color=m.YELLOW, stroke_width=2)

        self.add(rod1, rod2, joint_dot, end_dot, trace)
        self.play(t.animate.set_value(9.0), run_time=8.0, rate_func=m.linear)
        self.wait(1.0)
