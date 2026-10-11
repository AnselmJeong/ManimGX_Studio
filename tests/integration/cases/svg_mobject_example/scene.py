# Source: manimgx API coverage (CE 0.21 `SVGMobject`)
import manimgx as m


class SVGMobjectExample(m.Scene):
    def construct(self):
        shapes = m.SVGMobject("shapes.svg", height=4)
        self.play(m.Create(shapes), run_time=2)
        self.play(shapes.animate.rotate(m.PI / 8))
