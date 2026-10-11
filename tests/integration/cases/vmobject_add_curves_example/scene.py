# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VMobjectAddCurvesExample(m.Scene):
    def construct(self):
        line_path = m.VMobject(stroke_color=m.RED, stroke_width=8)
        line_path.set_points_as_corners([m.LEFT * 2 + m.DOWN, m.LEFT + m.DOWN])
        line_path.add_line_to(m.ORIGIN + m.DOWN)
        line_path.add_cubic_bezier_curve_to(
            m.LEFT + m.UP, m.RIGHT + m.UP, m.RIGHT + m.DOWN
        )
        line_path.add_quadratic_bezier_curve_to(
            m.RIGHT * 2 + m.UP, m.RIGHT * 2 + m.DOWN
        )

        smooth_path = m.VMobject(stroke_color=m.BLUE, stroke_width=6)
        smooth_path.set_points_as_corners(
            [m.LEFT * 2 + m.UP * 1.5, m.LEFT + m.UP * 1.5]
        )
        smooth_path.add_cubic_bezier_curve_to(
            m.LEFT + m.UP * 2.5, m.ORIGIN + m.UP * 2.5, m.UP * 1.5
        )
        smooth_path.add_smooth_curve_to(m.RIGHT * 2 + m.UP * 1.5)

        self.add(line_path, smooth_path)
        self.wait()
