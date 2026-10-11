# Source: manim/mobject/matrix.py
import manimgx as m


class MatrixExamples(m.Scene):
    def construct(self):
        m0 = m.Matrix([["\\pi", 0], [-1, 1]])
        m1 = m.IntegerMatrix(
            [[1.5, 0.0], [12, -1.3]], left_bracket="(", right_bracket=")"
        )
        m2 = m.DecimalMatrix(
            [[3.456, 2.122], [33.2244, 12.33]],
            element_to_mobject_config={"num_decimal_places": 2},
            left_bracket=r"\{",
            right_bracket=r"\}",
        )
        m3 = m.MobjectMatrix(
            [
                [m.Circle().scale(0.3), m.Square().scale(0.3)],
                [m.MathTex("\\pi").scale(2), m.Star().scale(0.3)],
            ],
            left_bracket="\\langle",
            right_bracket="\\rangle",
        )
        g = m.Group(m0, m1, m2, m3).arrange_in_grid(buff=2)
        self.add(g)
        self.wait()
