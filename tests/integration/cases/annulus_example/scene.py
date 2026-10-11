# Source: manim/mobject/geometry/arc.py
import manimgx as m


class AnnulusExample(m.Scene):
    def construct(self):
        annulus_1 = m.Annulus(inner_radius=0.5, outer_radius=1).shift(m.UP)
        annulus_2 = m.Annulus(inner_radius=0.3, outer_radius=0.6, color=m.RED).next_to(
            annulus_1, m.DOWN
        )
        self.add(annulus_1, annulus_2)
        self.wait()
