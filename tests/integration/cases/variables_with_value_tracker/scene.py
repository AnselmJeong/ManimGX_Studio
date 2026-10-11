# Source: manim/mobject/text/numbers.py
import manimgx as m


class VariablesWithValueTracker(m.Scene):
    def construct(self):
        var = 0.5
        on_screen_var = m.Variable(var, m.Text("var"), num_decimal_places=3)

        # You can also change the colours for the label and value
        on_screen_var.label.set_color(m.RED)
        on_screen_var.value.set_color(m.GREEN)

        self.play(m.Write(on_screen_var))
        # The above line will just display the variable with
        # its initial value on the screen. If you also wish to
        # update it, you can do so by accessing the `tracker` attribute
        self.wait()
        var_tracker = on_screen_var.tracker
        var = 10.5
        self.play(var_tracker.animate.set_value(var))
        self.wait()

        int_var = 0
        on_screen_int_var = m.Variable(
            int_var, m.Text("int_var"), var_type=m.Integer
        ).next_to(on_screen_var, m.DOWN)
        on_screen_int_var.label.set_color(m.RED)
        on_screen_int_var.value.set_color(m.GREEN)

        self.play(m.Write(on_screen_int_var))
        self.wait()
        var_tracker = on_screen_int_var.tracker
        var = 10.5
        self.play(var_tracker.animate.set_value(var))
        self.wait()

        # If you wish to have a somewhat more complicated label for your
        # variable with subscripts, superscripts, etc. the default class
        # for the label is MathTex
        subscript_label_var = 10
        on_screen_subscript_var = m.Variable(subscript_label_var, "{a}_{i}").next_to(
            on_screen_int_var, m.DOWN
        )
        self.play(m.Write(on_screen_subscript_var))
        self.wait()
