# Source: manim/animation/transform.py
import manimgx as m


class FadeTransformSubmobjects(m.Scene):
    def construct(self):
        src = m.VGroup(m.Square(), m.Circle().shift(m.LEFT + m.UP))
        src.shift(3 * m.LEFT + 2 * m.UP)
        src_copy = src.copy().shift(4 * m.DOWN)

        target = m.VGroup(m.Circle(), m.Triangle().shift(m.RIGHT + m.DOWN))
        target.shift(3 * m.RIGHT + 2 * m.UP)
        target_copy = target.copy().shift(4 * m.DOWN)

        self.play(m.FadeIn(src), m.FadeIn(src_copy))
        self.play(
            m.FadeTransform(src, target),
            m.FadeTransformPieces(src_copy, target_copy),
        )
        self.play(*[m.FadeOut(mobj) for mobj in self.mobjects])
