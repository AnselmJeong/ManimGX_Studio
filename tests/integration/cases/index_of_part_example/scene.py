# Source: manimgx API coverage (CE 0.21 `MathTex.index_of_part`)
import manimgx as m


class IndexOfPartExample(m.Scene):
    def construct(self):
        equation = m.MathTex("x", "=", "y", "+", "z").scale(2)
        self.add(equation)
        i = equation.index_of_part(equation[2])
        self.play(
            equation[i].animate.set_color(m.YELLOW),
            equation[i + 2].animate.set_color(m.TEAL),
        )
