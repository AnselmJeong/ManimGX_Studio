# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class MobjectScaleExample(m.Scene):
    def construct(self):
        c1 = m.Circle(1, m.RED).set_x(-1)
        c2 = m.Circle(1, m.GREEN).set_x(1)

        vg = m.VGroup(c1, c2)
        vg.set_stroke(width=50)
        self.add(vg)

        self.play(c1.animate.scale(0.25), c2.animate.scale(0.25, scale_stroke=True))
