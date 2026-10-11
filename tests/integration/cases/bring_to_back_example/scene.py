# Source: manimgx API coverage (CE 0.21 `Scene.bring_to_back`)
import manimgx as m


class BringToBackExample(m.Scene):
    def construct(self):
        square = m.Square(side_length=3, color=m.BLUE, fill_opacity=1).shift(
            0.8 * m.LEFT
        )
        circle = m.Circle(radius=1.6, color=m.RED, fill_opacity=1).shift(0.8 * m.RIGHT)
        triangle = m.Triangle(color=m.GREEN, fill_opacity=1).scale(1.5)
        self.add(square, circle, triangle)
        self.wait(0.5)
        self.bring_to_back(triangle, circle)
        self.wait(0.5)
