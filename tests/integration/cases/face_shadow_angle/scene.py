import math

import numpy as np

import manimgx as m


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=-55 * m.DEGREES)

        title = m.Tex("Face shadow $= \\cos(\\theta) \\cdot A$").to_corner(
            m.UL, buff=0.3
        )
        self.add_fixed_in_frame_mobjects(title)
        self.play(m.Write(title))

        floor = m.Square(
            side_length=4,
            color=m.GREY_B,
            stroke_width=1,
            fill_color=m.GREY_D,
            fill_opacity=0.3,
        )

        theta = m.ValueTracker(0.0)

        def make_face() -> m.VMobject:
            face = m.Square(
                side_length=1.4,
                color=m.BLUE,
                fill_color=m.BLUE,
                fill_opacity=0.6,
                stroke_width=2,
            )
            face.rotate(theta.get_value(), axis=np.array([1.0, 0.0, 0.0]))
            face.shift(m.OUT * 0.9)
            return face

        face = m.always_redraw(make_face)

        def make_shadow() -> m.VMobject:
            angle = theta.get_value()
            # face originally in xy plane with side 1.4 → after rotating about x by θ,
            # y-extent becomes 1.4 * cos(θ). Shadow on z=0 is rectangle 1.4 × 1.4 cos θ.
            w = 0.7
            h = 0.7 * abs(math.cos(angle))
            return m.Polygon(
                [-w, -h, 0.005],
                [w, -h, 0.005],
                [w, h, 0.005],
                [-w, h, 0.005],
                color=m.BLACK,
                fill_color=m.BLACK,
                fill_opacity=0.55,
                stroke_width=1.5,
            )

        shadow = m.always_redraw(make_shadow)

        self.play(m.Create(floor))
        self.add(face, shadow)
        self.play(
            theta.animate.set_value(math.pi / 3), run_time=2.5, rate_func=m.linear
        )
        self.play(
            theta.animate.set_value(math.pi / 2 - 0.05),
            run_time=2.0,
            rate_func=m.linear,
        )
        self.wait(1.0)
