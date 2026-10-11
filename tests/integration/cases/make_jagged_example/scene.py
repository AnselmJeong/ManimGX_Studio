# Source: manimgx API coverage (CE 0.21 `VMobject.make_jagged`)
import manimgx as m


class MakeJaggedExample(m.Scene):
    def construct(self):
        points = [[-4, -1, 0], [-2, 1, 0], [0, -1, 0], [2, 1, 0], [4, -1, 0]]
        curve = m.VMobject(color=m.PINK, stroke_width=6).set_points_smoothly(points)
        self.add(curve)
        self.play(m.Transform(curve, curve.copy().make_jagged().set_color(m.TEAL)))
