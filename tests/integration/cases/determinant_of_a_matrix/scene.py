# Source: manim/mobject/matrix.py
import manimgx as m


class DeterminantOfAMatrix(m.Scene):
    def construct(self):
        matrix = m.Matrix([[2, 0], [-1, 1]])

        # scaling down the `det` string
        initial_scale_factor = 1
        parens = m.MathTex("(", ")")
        parens.scale(initial_scale_factor)
        parens.stretch_to_fit_height(matrix.height)
        l_paren, r_paren = parens
        l_paren.next_to(matrix, m.LEFT, buff=0.1)
        r_paren.next_to(matrix, m.RIGHT, buff=0.1)
        det_label = m.Tex("det")
        det_label.scale(initial_scale_factor)
        det_label.next_to(l_paren, m.LEFT, buff=0.1)
        eq = m.MathTex("=")
        eq.next_to(r_paren, m.RIGHT, buff=0.1)
        result = m.MathTex("3")
        result.next_to(eq, m.RIGHT, buff=0.2)
        det = m.VGroup(det_label, l_paren, r_paren, eq, result)

        # must add the matrix
        self.add(matrix)
        self.add(det)
