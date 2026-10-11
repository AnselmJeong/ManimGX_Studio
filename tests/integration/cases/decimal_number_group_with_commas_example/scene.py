# Source: manim/mobject/text/numbers.py
import manimgx as m


class DecimalNumberGroupWithCommasExample(m.Scene):
    def construct(self):
        number = m.DecimalNumber(
            1234567.89,
            num_decimal_places=2,
            group_with_commas=True,
            font_size=60,
        )
        self.play(m.FadeIn(number))
        self.wait(0.2)
