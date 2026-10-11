# Source: docs/source/tutorials/quickstart.rst
import manimgx as m


class CreateCircle(m.Scene):
    def construct(self):
        circle = m.Circle()  # create a circle
        circle.set_fill(m.PINK, opacity=0.5)  # set the color and transparency
        self.play(m.Create(circle))  # show the circle on screen
