# Source: manim/mobject/mobject.py
import manimgx as m


class AnimateWithArgsExample(m.Scene):
    def construct(self):
        s = m.Square()
        c = m.Circle()

        m.VGroup(s, c).arrange(m.RIGHT, buff=2)
        self.add(s, c)

        self.play(
            m.Rotate(s, angle=m.PI / 2, run_time=2),
            c.animate(rate_func=m.there_and_back).shift(m.RIGHT),
        )
