# Source: docs/source/guides/using_text.rst
import manimgx as m


class DifferentWeight(m.Scene):
    def construct(self):
        g = m.VGroup()
        # the guide's list, manimpango.Weight lightest to heaviest: Pango's weights, by name
        for weight in (
            m.THIN,
            m.ULTRALIGHT,
            m.LIGHT,
            m.BOOK,
            m.NORMAL,
            m.MEDIUM,
            m.SEMIBOLD,
            m.BOLD,
            m.ULTRABOLD,
            m.HEAVY,
            m.ULTRAHEAVY,
        ):
            g += m.Text(weight, weight=weight, font="Open Sans")
        self.add(g.arrange(m.DOWN).scale(0.5))
