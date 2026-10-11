# Source: manimgx API coverage (CE 0.21 `MathTypst`)
import manimgx as m


class MathTypstExample(m.Scene):
    def construct(self):
        equation = m.MathTypst("{{ a^2 + b^2 : lhs }} = {{ c^2 }}", font_size=72)
        equation.select("lhs").set_color(m.BLUE)
        equation.select(0).set_color(m.YELLOW)
        self.play(m.FadeIn(equation))
        self.play(equation.select("lhs").animate.shift(0.5 * m.UP))
