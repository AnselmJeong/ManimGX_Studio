# Source: manim/animation/numbers.py
import manimgx as m


class ChangingDecimalExample(m.Scene):
    def construct(self):
        number = m.DecimalNumber(0)
        self.add(number)
        self.play(m.ChangingDecimal(number, lambda a: 5 * a, run_time=3))
        self.wait()
