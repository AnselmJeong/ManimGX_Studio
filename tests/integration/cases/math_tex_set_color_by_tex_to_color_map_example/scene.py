# Source: manim/mobject/text/tex_mobject.py
import manimgx as m


class MathTexSetColorByTexToColorMapExample(m.Scene):
    def construct(self):
        equation = m.MathTex("x", "+", "y", "=", "z", font_size=72)
        equation.set_color_by_tex_to_color_map({"x": m.RED, "y": m.GREEN, "z": m.BLUE})
        self.play(m.FadeIn(equation))
        self.wait(0.2)
