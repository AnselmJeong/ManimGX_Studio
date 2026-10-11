# Source: docs/source/tutorials/quickstart.rst
import manimgx as m


class AnimatedSquareToCircle2(m.Scene):
    def construct(self):
        circle = m.Circle()  # create a circle
        square = m.Square()  # create a square

        self.play(m.Create(square))  # show the square on screen
        self.play(m.Rotate(square, angle=m.PI / 4))  # rotate the square
        self.play(m.Transform(square, circle))  # transform the square into a circle
        self.play(
            square.animate.set_fill(m.PINK, opacity=0.5)
        )  # color the circle on screen
