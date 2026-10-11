# Source: manim/utils/color/core.py
import manimgx as m


class ManimColorGradientDemo(m.Scene):
    def construct(self):
        gradient = m.color_gradient([m.RED, m.YELLOW, m.GREEN, m.BLUE], 12)
        bars = m.VGroup(
            *[
                m.Rectangle(width=0.5, height=2.0, fill_color=c, fill_opacity=1.0)
                for c in gradient
            ]
        ).arrange(buff=0.0)

        avg = m.average_color(m.RED, m.BLUE, m.GREEN)
        mid = m.interpolate_color(m.RED, m.BLUE, 0.5)

        avg_square = m.Square(side_length=0.8, fill_color=avg, fill_opacity=1.0)
        mid_square = m.Square(side_length=0.8, fill_color=mid, fill_opacity=1.0)
        accents = (
            m.VGroup(avg_square, mid_square)
            .arrange(buff=0.2)
            .next_to(bars, m.DOWN, buff=0.4)
        )

        self.add(bars, accents)
        self.wait(1)
