# Source: manim/utils/paths.py
import manimgx as m


class PathAlongCirclesExample(m.Scene):
    def construct(self):
        colors = [m.RED, m.GREEN, m.BLUE]

        starting_points = m.VGroup(
            *[
                m.Dot(m.LEFT + pos, color=color)
                for pos, color in zip([m.UP, m.DOWN, m.LEFT], colors)
            ]
        )

        finish_points = m.VGroup(
            *[
                m.Dot(m.RIGHT + pos, color=color)
                for pos, color in zip([m.ORIGIN, m.UP, m.DOWN], colors)
            ]
        )

        self.add(starting_points)
        self.add(finish_points)
        for dot in starting_points:
            self.add(m.TracedPath(dot.get_center, stroke_color=dot.get_color()))

        circle_center = m.Dot(3 * m.LEFT)
        self.add(circle_center)

        self.wait()
        self.play(
            m.Transform(
                starting_points,
                finish_points,
                path_func=m.path_along_circles(2 * m.PI, circle_center.get_center()),
                run_time=3,
            )
        )
        self.wait()
