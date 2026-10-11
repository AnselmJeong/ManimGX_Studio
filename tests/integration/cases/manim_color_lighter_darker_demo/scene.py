# Source: manim/utils/color/core.py
import manimgx as m


class ManimColorLighterDarkerDemo(m.Scene):
    def construct(self):
        base_colors = [m.RED, m.GREEN, m.BLUE, m.YELLOW, m.PURPLE]
        rows = m.VGroup()
        for base in base_colors:
            row = m.VGroup(
                m.Square(
                    side_length=0.6, fill_color=base.darker(0.6), fill_opacity=1.0
                ),
                m.Square(
                    side_length=0.6, fill_color=base.darker(0.3), fill_opacity=1.0
                ),
                m.Square(side_length=0.6, fill_color=base, fill_opacity=1.0),
                m.Square(
                    side_length=0.6, fill_color=base.lighter(0.3), fill_opacity=1.0
                ),
                m.Square(
                    side_length=0.6, fill_color=base.lighter(0.6), fill_opacity=1.0
                ),
            ).arrange(buff=0.1)
            rows.add(row)
        rows.arrange(buff=0.15, direction=m.DOWN)
        self.add(rows)
        self.wait(1)
