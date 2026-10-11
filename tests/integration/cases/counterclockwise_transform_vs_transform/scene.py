# Source: manim/animation/transform.py
import manimgx as m


class CounterclockwiseTransform_vs_Transform(m.Scene):
    def construct(self):
        # set up the numbers
        c_transform = m.VGroup(
            m.DecimalNumber(number=3.141, num_decimal_places=3),
            m.DecimalNumber(number=1.618, num_decimal_places=3),
        )
        text_1 = m.Text("CounterclockwiseTransform", color=m.RED)
        c_transform.add(text_1)

        transform = m.VGroup(
            m.DecimalNumber(number=1.618, num_decimal_places=3),
            m.DecimalNumber(number=3.141, num_decimal_places=3),
        )
        text_2 = m.Text("Transform", color=m.BLUE)
        transform.add(text_2)

        ints = m.VGroup(c_transform, transform)
        texts = m.VGroup(text_1, text_2).scale(0.75)
        c_transform.arrange(direction=m.UP, buff=1)
        transform.arrange(direction=m.UP, buff=1)

        ints.arrange(buff=2)
        self.add(ints, texts)

        # The mobs move in clockwise direction for ClockwiseTransform()
        self.play(m.CounterclockwiseTransform(c_transform[0], c_transform[1]))

        # The mobs move straight up for Transform()
        self.play(m.Transform(transform[0], transform[1]))
