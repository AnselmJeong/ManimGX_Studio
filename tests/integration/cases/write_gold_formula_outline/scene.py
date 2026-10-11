# Source: completing-the-square outro — Write outline-colour regression.
# Writing a fill-only coloured MathTex must draw the outline pass in the
# glyph's own colour (one smooth gold wave), not white: a white outline used
# to sweep ahead of the gold fill (a visible "double wave"), and each glyph —
# e.g. the first ^2 — appeared white, faded, then returned gold.
import manimgx as m


class WriteGoldFormulaOutline(m.Scene):
    def construct(self):
        general_eq = m.MathTex(
            r"x^2 + b x = \left( x + \frac{b}{2} \right)^2 - \left( \frac{b}{2}"
            r" \right)^2",
            font_size=38,
            color="#F59E0B",
        )
        self.play(m.Write(general_eq))
        self.wait(0.5)
