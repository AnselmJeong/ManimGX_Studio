# Source: manim/utils/color/core.py
import manimgx as m


class ManimColorRandomGeneratorDemo(m.Scene):
    def construct(self):
        palette = [m.RED, m.GREEN, m.BLUE, m.YELLOW, m.PURPLE, m.TEAL]
        gen = m.RandomColorGenerator(seed=7, sample_colors=palette)

        rows = m.VGroup()
        for _ in range(4):
            row = m.VGroup(
                *[
                    m.Square(side_length=0.5, fill_color=gen.next(), fill_opacity=1.0)
                    for _ in range(8)
                ]
            ).arrange(buff=0.08)
            rows.add(row)
        rows.arrange(buff=0.12, direction=m.DOWN)

        self.add(rows)
        self.wait(1)
