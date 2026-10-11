# Source: manimgx API coverage (CE 0.21 `VMobject.close_path`)
import manimgx as m


class ClosePathExample(m.Scene):
    def construct(self):
        path = m.VMobject(color=m.GREEN, stroke_width=6)
        path.set_points_as_corners([[-2, -1, 0], [0, 2, 0], [2, -1, 0]])
        path.close_path()
        self.play(m.Create(path))
        self.play(path.animate.set_fill(m.GREEN, 0.5))
