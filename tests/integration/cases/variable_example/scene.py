# Source: manim/mobject/text/numbers.py
import manimgx as m


class VariableExample(m.Scene):
    def construct(self):
        start = 2.0

        x_var = m.Variable(start, "x", num_decimal_places=3)
        sqr_var = m.Variable(start**2, "x^2", num_decimal_places=3)
        m.Group(x_var, sqr_var).arrange(m.DOWN)

        sqr_var.add_updater(
            lambda v: v.tracker.set_value(x_var.tracker.get_value() ** 2)
        )

        self.add(x_var, sqr_var)
        self.play(x_var.tracker.animate.set_value(5), run_time=2, rate_func=m.linear)
        self.wait(0.1)
