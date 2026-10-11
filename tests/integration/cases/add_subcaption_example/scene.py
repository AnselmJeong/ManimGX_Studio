# Source: manimgx API coverage (CE 0.21 `Scene.add_subcaption`)
import manimgx as m


class AddSubcaptionExample(m.Scene):
    def construct(self):
        square = m.Square(color=m.BLUE)
        self.add_subcaption("A square appears", duration=1)
        self.play(m.Create(square))
        self.add_subcaption("and turns", duration=1, offset=0.2)
        self.play(m.Rotate(square, m.PI / 4))
