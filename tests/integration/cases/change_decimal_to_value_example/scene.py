# Source: manim/animation/numbers.py
import manimgx as m


class ChangeDecimalToValueExample(m.Scene):
    def construct(self):
        number = m.DecimalNumber(0)
        self.add(number)
        self.play(m.ChangeDecimalToValue(number, 10, run_time=3))
        self.wait()
