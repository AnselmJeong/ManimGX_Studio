# Source: docs/source/examples.rst
import manimgx as m


class PointMovingOnShapes(m.Scene):
    def construct(self):
        circle = m.Circle(radius=1, color=m.BLUE)
        dot = m.Dot()
        dot2 = dot.copy().shift(m.RIGHT)
        self.add(dot)

        line = m.Line([3, 0, 0], [5, 0, 0])
        self.add(line)

        self.play(m.GrowFromCenter(circle))
        self.play(m.Transform(dot, dot2))
        self.play(m.MoveAlongPath(dot, circle), run_time=2, rate_func=m.linear)
        self.play(m.Rotating(dot, about_point=[2, 0, 0]), run_time=1.5)
        self.wait()
