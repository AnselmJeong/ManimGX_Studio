# Source: manim/animation/transform_matching_parts.py
import manimgx as m


class MatchingEquationParts(m.Scene):
    def construct(self):
        variables = (
            m.VGroup(m.MathTex("a"), m.MathTex("b"), m.MathTex("c"))
            .arrange_submobjects()
            .shift(m.UP)
        )

        eq1 = m.MathTex("{{x}}^2", "+", "{{y}}^2", "=", "{{z}}^2")
        eq2 = m.MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2")
        eq3 = m.MathTex("{{a}}^2", "=", "{{c}}^2", "-", "{{b}}^2")

        self.add(eq1)
        self.wait(0.5)
        self.play(m.TransformMatchingTex(m.Group(eq1, variables), eq2))
        self.wait(0.5)
        self.play(m.TransformMatchingTex(eq2, eq3))
        self.wait(0.5)
