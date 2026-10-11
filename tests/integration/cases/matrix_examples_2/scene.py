# Source: manim/mobject/matrix.py
import manimgx as m


class MatrixExamples(m.Scene):
    def construct(self):
        m0 = m.Matrix([[2, r"\pi"], [-1, 1]])
        m1 = m.Matrix(
            [[2, 0, 4], [-1, 1, 5]],
            v_buff=1.3,
            h_buff=0.8,
            bracket_h_buff=m.SMALL_BUFF,
            bracket_v_buff=m.SMALL_BUFF,
            left_bracket=r"\{",
            right_bracket=r"\}",
        )
        m1.add(m.SurroundingRectangle(m1.get_columns()[1]))
        m2 = m.Matrix(
            [[2, 1], [-1, 3]],
            element_alignment_corner=m.UL,
            left_bracket="(",
            right_bracket=")",
        )
        m3 = m.Matrix(
            [[2, 1], [-1, 3]], left_bracket=r"\langle", right_bracket=r"\rangle"
        )
        m4 = m.Matrix(
            [[2, 1], [-1, 3]],
        ).set_column_colors(m.RED, m.GREEN)
        m5 = m.Matrix(
            [[2, 1], [-1, 3]],
        ).set_row_colors(m.RED, m.GREEN)
        g = m.Group(m0, m1, m2, m3, m4, m5).arrange_in_grid(buff=2)
        self.add(g)
        self.wait()
