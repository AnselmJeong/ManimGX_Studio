# Source: manimgx API coverage (CE 0.21 `Scene.bring_to_front`)
import manimgx as m


class BringToFrontExample(m.Scene):
    def construct(self):
        square = m.Square(side_length=3, color=m.BLUE, fill_opacity=1).shift(
            0.8 * m.LEFT
        )
        circle = m.Circle(radius=1.6, color=m.RED, fill_opacity=1).shift(0.8 * m.RIGHT)
        self.add(square, circle)
        self.wait(0.5)
        self.bring_to_front(square)
        self.wait(0.5)
