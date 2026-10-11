# Source: manim/mobject/table.py
import manimgx as m


class IntegerTableExample(m.Scene):
    def construct(self):
        t0 = m.IntegerTable(
            [[0, 30, 45, 60, 90], [90, 60, 45, 30, 0]],
            col_labels=[
                m.Tex(r"$\frac{ \sqrt{0} }{2}$"),
                m.Tex(r"$\frac{ \sqrt{1} }{2}$"),
                m.Tex(r"$\frac{ \sqrt{2} }{2}$"),
                m.Tex(r"$\frac{ \sqrt{3} }{2}$"),
                m.Tex(r"$\frac{ \sqrt{4} }{2}$"),
            ],
            row_labels=[m.MathTex(r"\sin"), m.MathTex(r"\cos")],
            h_buff=1,
            element_to_mobject_config={"unit": r"^{\circ}"},
        )
        self.add(t0)
        self.wait()
