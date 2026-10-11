# Source: manim/animation/transform.py
import manimgx as m


class ClockwiseExample(m.Scene):
    def construct(self):
        dl, dr = m.Dot(), m.Dot()
        sl, sr = m.Square(), m.Square()

        m.VGroup(dl, sl).arrange(m.DOWN).shift(2 * m.LEFT)
        m.VGroup(dr, sr).arrange(m.DOWN).shift(2 * m.RIGHT)

        self.add(dl, dr)
        self.wait()
        self.play(m.ClockwiseTransform(dl, sl), m.Transform(dr, sr))
        self.wait()
