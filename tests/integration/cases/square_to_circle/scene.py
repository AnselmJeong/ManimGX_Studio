# Source: example_scenes/basic.py
import manimgx as m


class SquareToCircle(m.Scene):
    def construct(self):
        circle = m.Circle()
        square = m.Square()
        square.flip(m.RIGHT)
        square.rotate(-3 * m.TAU / 8)
        circle.set_fill(m.PINK, opacity=0.5)

        self.play(m.Create(square))
        self.play(m.Transform(square, circle))
        self.play(m.FadeOut(square))
