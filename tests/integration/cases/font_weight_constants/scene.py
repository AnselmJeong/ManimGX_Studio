# Source: manim/constants.py
import manimgx as m


class FontWeightConstants(m.Scene):
    def construct(self):
        all_weights = (
            m.NORMAL,
            m.BOLD,
            m.THIN,
            m.ULTRALIGHT,
            m.LIGHT,
            m.SEMILIGHT,
            m.BOOK,
            m.MEDIUM,
            m.SEMIBOLD,
            m.ULTRABOLD,
            m.HEAVY,
            m.ULTRAHEAVY,
        )
        label = m.Text(", ".join(all_weights), weight=m.BOLD, font_size=18)
        self.add(label)
        self.wait()
