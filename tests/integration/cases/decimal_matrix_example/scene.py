# Source: manim/mobject/matrix.py
import manimgx as m


class DecimalMatrixExample(m.Scene):
    def construct(self):
        m0 = m.DecimalMatrix(
            [[3.456, 2.122], [33.2244, 12]],
            element_to_mobject_config={"num_decimal_places": 2},
            left_bracket="\\{",
            right_bracket="\\}",
        )
        self.add(m0)
        self.wait()
