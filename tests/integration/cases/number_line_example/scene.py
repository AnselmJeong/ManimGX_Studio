# Source: manim/mobject/graphing/number_line.py
import manimgx as m


class NumberLineExample(m.Scene):
    def construct(self):
        l0 = m.NumberLine(
            x_range=[-10, 10, 2],
            length=10,
            color=m.BLUE,
            include_numbers=True,
            label_direction=m.UP,
        )

        l1 = m.NumberLine(
            x_range=[-10, 10, 2],
            unit_size=0.5,
            numbers_with_elongated_ticks=[-2, 4],
            include_numbers=True,
            font_size=24,
        )
        num6 = l1.numbers[8]
        num6.set_color(m.RED)

        l2 = m.NumberLine(
            x_range=[-2.5, 2.5 + 0.5, 0.5],
            length=12,
            decimal_number_config={"num_decimal_places": 2},
            include_numbers=True,
        )

        l3 = m.NumberLine(
            x_range=[-5, 5 + 1, 1],
            length=6,
            include_tip=True,
            include_numbers=True,
            rotation=10 * m.DEGREES,
        )

        line_group = m.VGroup(l0, l1, l2, l3).arrange(m.DOWN, buff=1)
        self.add(line_group)
        self.wait()
