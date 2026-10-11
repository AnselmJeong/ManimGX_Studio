import manimgx as m


class MathTexSplitLeftRightDelimiters(m.Scene):
    def construct(self):
        # A `\left[ ... \right]` group split across three MathTex arguments,
        # the CE idiom for making the middle (Reynolds-stress) term separately
        # addressable so it can be colored. The opening `\left[` lives in the
        # first argument and the matching `\right]` in the third; neither is a
        # balanced expression on its own.
        eq = m.MathTex(
            r"\frac{\partial}{\partial x_j} \left[ \mu \left( \frac{\partial"
            r" u_i}{\partial x_j} \right)",
            r"- \rho \overline{u_i u_j}",
            r"\right]",
            font_size=44,
        )
        eq[1].set_color(m.RED)
        self.add(eq)
