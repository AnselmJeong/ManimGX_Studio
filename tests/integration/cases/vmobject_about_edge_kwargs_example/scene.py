# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VMobjectAboutEdgeKwargsExample(m.Scene):
    def construct(self):
        base = m.Square(side_length=1.5, color=m.GREY)
        rotated = (
            m.Square(side_length=1.5, color=m.RED)
            .move_to(m.LEFT * 2)
            .rotate(0.6, about_edge=m.LEFT)
        )
        scaled = (
            m.Square(side_length=1.5, color=m.GREEN)
            .move_to(m.RIGHT * 2)
            .scale(scale_factor=1.4, about_edge=m.RIGHT)
        )
        shifted = (
            m.Square(side_length=1.0, color=m.BLUE)
            .move_to(m.UP * 2)
            .apply_function(lambda point: point + m.RIGHT * 0.5, about_edge=m.DOWN)
        )
        self.add(base, rotated, scaled, shifted)
        self.wait()
