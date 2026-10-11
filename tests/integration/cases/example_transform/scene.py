# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class ExampleTransform(m.Scene):
    def construct(self):
        self.camera.background_color = m.WHITE
        m1 = m.Square().set_color(m.RED)
        m2 = m.Rectangle().set_color(m.RED).rotate(0.2)
        self.play(m.Transform(m1, m2))
