# Source: manimgx API coverage (CE 0.21 `VMobject.add_subpath`)
import manimgx as m


class AddSubpathExample(m.Scene):
    def construct(self):
        shape = m.VMobject(color=m.BLUE, fill_opacity=0.6)
        shape.set_points_as_corners([[-3, -1, 0], [-1, -1, 0], [-2, 1, 0], [-3, -1, 0]])
        shape.add_subpath(m.Square(side_length=2).shift(2 * m.RIGHT).points)
        self.play(m.FadeIn(shape))
        self.play(shape.animate.set_fill(m.GREEN, 0.9))
