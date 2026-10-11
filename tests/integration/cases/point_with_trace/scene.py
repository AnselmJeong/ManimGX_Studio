# Source: docs/source/examples.rst
import manimgx as m


class PointWithTrace(m.Scene):
    def construct(self):
        path = m.VMobject()
        dot = m.Dot()
        path.set_points_as_corners([dot.get_center(), dot.get_center()])

        def update_path(path):
            previous_path = path.copy()
            previous_path.add_points_as_corners([dot.get_center()])
            path.become(previous_path)

        path.add_updater(update_path)
        self.add(path, dot)
        self.play(m.Rotating(dot, angle=m.PI, about_point=m.RIGHT, run_time=2))
        self.wait()
        self.play(dot.animate.shift(m.UP))
        self.play(dot.animate.shift(m.LEFT))
        self.wait()
