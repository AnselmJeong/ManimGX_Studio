# Source: docs/source/tutorials/output_and_config.rst
import manimgx as m


class SquareToCircle3(m.Scene):
    def construct(self):
        circle = m.Circle()  # create a circle
        circle.set_fill(m.PINK, opacity=0.5)  # set color and transparency

        square = m.Square()  # create a square
        square.flip(m.RIGHT)  # flip horizontally
        square.rotate(-3 * m.TAU / 8)  # rotate a certain amount

        self.play(m.Create(square))  # animate the creation of the square
        self.play(m.Transform(square, circle))  # interpolate the square into the circle
        self.play(m.FadeOut(square))  # fade out animation
