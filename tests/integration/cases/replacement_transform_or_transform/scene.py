# Source: manim/animation/transform.py
import manimgx as m


class ReplacementTransformOrTransform(m.Scene):
    def construct(self):
        # set up the numbers
        r_transform = m.VGroup(*[m.Integer(i) for i in range(1, 4)])
        text_1 = m.Text("ReplacementTransform", color=m.RED)
        r_transform.add(text_1)

        transform = m.VGroup(*[m.Integer(i) for i in range(4, 7)])
        text_2 = m.Text("Transform", color=m.BLUE)
        transform.add(text_2)

        ints = m.VGroup(r_transform, transform)
        texts = m.VGroup(text_1, text_2).scale(0.75)
        r_transform.arrange(direction=m.UP, buff=1)
        transform.arrange(direction=m.UP, buff=1)

        ints.arrange(buff=2)
        self.add(ints, texts)

        # The mobs replace each other and none are left behind
        self.play(m.ReplacementTransform(r_transform[0], r_transform[1]))
        self.play(m.ReplacementTransform(r_transform[1], r_transform[2]))

        # The mobs linger after the Transform()
        self.play(m.Transform(transform[0], transform[1]))
        self.play(m.Transform(transform[1], transform[2]))
        self.wait()
