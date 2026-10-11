# Source: manimgx API coverage (CE 0.21 `MathTex.get_part_by_tex`)
import manimgx as m


class GetPartByTexExample(m.Scene):
    def construct(self):
        equation = m.MathTex("a^2", "+", "b^2", "=", "c^2").scale(2)
        part = equation.get_part_by_tex("b^2")
        if part is not None:
            part.set_color(m.RED)
        self.play(m.Write(equation))
        hypotenuse = equation.get_part_by_tex("c^2")
        if hypotenuse is not None:
            self.play(hypotenuse.animate.set_color(m.YELLOW).scale(1.3))
