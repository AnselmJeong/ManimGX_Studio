# Source: docs/source/tutorials/quickstart.rst
import manimgx as m


class SquareAndCircle2(m.Scene):
    def construct(self):
        circle = m.Circle()  # create a circle
        circle.set_fill(m.PINK, opacity=0.5)  # set the color and transparency

        square = m.Square()  # create a square
        square.set_fill(m.BLUE, opacity=0.5)  # set the color and transparency

        square.next_to(circle, m.RIGHT, buff=0.5)  # set the position
        self.play(m.Create(circle), m.Create(square))  # show the shapes on screen
