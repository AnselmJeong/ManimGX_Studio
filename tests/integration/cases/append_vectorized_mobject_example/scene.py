# Source: manimgx API coverage (CE 0.21 `VMobject.append_vectorized_mobject`)
import manimgx as m


class AppendVectorizedMobjectExample(m.Scene):
    def construct(self):
        path = m.VMobject(color=m.ORANGE, stroke_width=6)
        path.set_points_as_corners([[-4, -1, 0], [-2, 1, 0], [0, -1, 0]])
        path.append_vectorized_mobject(
            m.Arc(radius=1, start_angle=m.PI, angle=-m.PI).shift(m.RIGHT + m.DOWN)
        )
        self.play(m.Create(path), run_time=2)
