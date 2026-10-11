# Source: manim/utils/color/core.py
import manimgx as m


class ManimColorHsvClassDemo(m.Scene):
    def construct(self):
        wheel = m.VGroup(
            *[
                m.Square(
                    side_length=0.7,
                    fill_color=m.HSV((i / 12, 0.85, 0.95)),
                    fill_opacity=1.0,
                )
                for i in range(12)
            ]
        ).arrange(buff=0.1)

        rotated = m.RED.into(m.HSV)
        rotated.h = (rotated.h + 0.5) % 1.0
        recovered = rotated.into(m.ManimColor)

        accent = (
            m.VGroup(
                m.Square(side_length=1.0, fill_color=m.RED, fill_opacity=1.0),
                m.Square(side_length=1.0, fill_color=recovered, fill_opacity=1.0),
            )
            .arrange(buff=0.3)
            .next_to(wheel, m.DOWN, buff=0.5)
        )

        self.add(wheel, accent)
        self.wait(1)
