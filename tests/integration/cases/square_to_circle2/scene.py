# Source: docs/source/tutorials/quickstart.rst
import manimgx as m


class SquareToCircle2(m.Scene):
    def construct(self):
        circle = m.Circle()  # create a circle
        circle.set_fill(m.PINK, opacity=0.5)  # set color and transparency

        square = m.Square()  # create a square
        square.rotate(m.PI / 4)  # rotate a certain amount

        self.play(m.Create(square))  # animate the creation of the square
        self.play(m.Transform(square, circle))  # interpolate the square into the circle
        self.play(m.FadeOut(square))  # fade out animation
