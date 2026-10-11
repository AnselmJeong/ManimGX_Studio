import math

import numpy as np

import manimgx as m

NUM_POINTS = 14


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-40 * m.DEGREES)
        axes = m.ThreeDAxes(
            x_range=[-4, 4, 1],
            y_range=[-2, 2, 1],
            z_range=[-2, 2, 1],
        )
        self.add(axes)

        t = m.ValueTracker(0.0)

        def make_field() -> m.VGroup:
            arrows = m.VGroup()
            now = t.get_value()
            for i in range(NUM_POINTS):
                x = -3.5 + i * 0.5
                e_z = math.sin(x - now)
                b_y = math.sin(x - now)
                arrows.add(
                    m.Line(
                        np.array([x, 0.0, 0.0]),
                        np.array([x, 0.0, e_z]),
                        color=m.YELLOW,
                        stroke_width=3,
                    )
                )
                arrows.add(
                    m.Line(
                        np.array([x, 0.0, 0.0]),
                        np.array([x, b_y, 0.0]),
                        color=m.BLUE,
                        stroke_width=3,
                    )
                )
            return arrows

        self.add(m.always_redraw(make_field))

        title = (
            m.Tex("E (yellow), B (blue) oscillate perpendicular to propagation")
            .scale(0.6)
            .to_edge(m.UP, buff=0.3)
        )
        self.add_fixed_in_frame_mobjects(title)

        self.play(t.animate.set_value(4 * math.pi), run_time=6.0, rate_func=m.linear)
        self.wait(1.0)
