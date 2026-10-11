# Source: manim/animation/transform.py
import manimgx as m


class DifferentFadeTransforms(m.Scene):
    def construct(self):
        starts = [m.Rectangle(width=4, height=1) for _ in range(3)]
        m.VGroup(*starts).arrange(m.DOWN, buff=1).shift(3 * m.LEFT)
        targets = [m.Circle(fill_opacity=1).scale(0.25) for _ in range(3)]
        m.VGroup(*targets).arrange(m.DOWN, buff=1).shift(3 * m.RIGHT)

        self.play(*[m.FadeIn(s) for s in starts])
        self.play(
            m.FadeTransform(starts[0], targets[0], stretch=True),
            m.FadeTransform(starts[1], targets[1], stretch=False, dim_to_match=0),
            m.FadeTransform(starts[2], targets[2], stretch=False, dim_to_match=1),
        )

        self.play(*[m.FadeOut(mobj) for mobj in self.mobjects])
