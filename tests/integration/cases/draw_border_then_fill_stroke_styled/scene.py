# Source: manim/animation/creation.py
import manimgx as m


class DrawBorderThenFillStrokeStyled(m.Scene):
    def construct(self):
        self.play(
            m.DrawBorderThenFill(
                m.Square(fill_opacity=1, fill_color=m.ORANGE),
                stroke_color=m.BLUE,
                stroke_width=6,
            )
        )
        self.wait(0.2)
