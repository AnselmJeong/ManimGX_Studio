# Source: manim/utils/color/manim_colors.py
import manimgx as m


class LogoColorsExample(m.Scene):
    def construct(self):
        swatches = m.Group(
            m.Square(side_length=1.0, color=m.LOGO_WHITE, fill_opacity=1),
            m.Square(side_length=1.0, color=m.LOGO_GREEN, fill_opacity=1),
            m.Square(side_length=1.0, color=m.LOGO_BLUE, fill_opacity=1),
            m.Square(side_length=1.0, color=m.LOGO_RED, fill_opacity=1),
            m.Square(side_length=1.0, color=m.LOGO_BLACK, fill_opacity=1),
        ).arrange(m.RIGHT, buff=0.2)
        self.add(swatches)
        self.wait()
