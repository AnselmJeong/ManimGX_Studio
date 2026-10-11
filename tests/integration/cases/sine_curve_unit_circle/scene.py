# Source: docs/source/examples.rst
import numpy as np

import manimgx as m


class SineCurveUnitCircle(m.Scene):
    # contributed by heejin_park, https://infograph.tistory.com/230
    def construct(self):
        self.show_axis()
        self.show_circle()
        self.move_dot_and_draw_curve()
        self.wait()

    def show_axis(self):
        x_start = np.array([-6, 0, 0])
        x_end = np.array([6, 0, 0])

        y_start = np.array([-4, -2, 0])
        y_end = np.array([-4, 2, 0])

        x_axis = m.Line(x_start, x_end)
        y_axis = m.Line(y_start, y_end)

        self.add(x_axis, y_axis)
        self.add_x_labels()

        self.origin_point = np.array([-4, 0, 0])
        self.curve_start = np.array([-3, 0, 0])

    def add_x_labels(self):
        x_labels = [
            m.MathTex(r"\pi"),
            m.MathTex(r"2 \pi"),
            m.MathTex(r"3 \pi"),
            m.MathTex(r"4 \pi"),
        ]

        for i in range(len(x_labels)):
            x_labels[i].next_to(np.array([-1 + 2 * i, 0, 0]), m.DOWN)
            self.add(x_labels[i])

    def show_circle(self):
        circle = m.Circle(radius=1)
        circle.move_to(self.origin_point)
        self.add(circle)
        self.circle = circle

    def move_dot_and_draw_curve(self):
        orbit = self.circle
        origin_point = self.origin_point

        dot = m.Dot(radius=0.08, color=m.YELLOW)
        dot.move_to(orbit.point_from_proportion(0))
        self.t_offset = 0
        rate = 0.25

        def go_around_circle(mob, dt):
            self.t_offset += dt * rate
            # print(self.t_offset)
            mob.move_to(orbit.point_from_proportion(self.t_offset % 1))

        def get_line_to_circle() -> m.Line:
            return m.Line(origin_point, dot.get_center(), color=m.BLUE)

        def get_line_to_curve() -> m.Line:
            x = self.curve_start[0] + self.t_offset * 4
            y = dot.get_center()[1]
            return m.Line(
                dot.get_center(),
                np.array([x, y, 0]),
                color=m.YELLOW_A,
                stroke_width=2,
            )

        self.curve = m.VGroup()
        self.curve.add(m.Line(self.curve_start, self.curve_start))

        def get_curve() -> m.VGroup:
            last_line = self.curve[-1]
            assert isinstance(last_line, m.Line)
            x = self.curve_start[0] + self.t_offset * 4
            y = dot.get_center()[1]
            new_line = m.Line(
                last_line.get_end(),
                np.array([x, y, 0]),
                color=m.YELLOW_D,
            )
            self.curve.add(new_line)

            return self.curve

        dot.add_updater(go_around_circle)

        origin_to_circle_line = m.always_redraw(get_line_to_circle)
        dot_to_curve_line = m.always_redraw(get_line_to_curve)
        sine_curve_line = m.always_redraw(get_curve)

        self.add(dot)
        self.add(orbit, origin_to_circle_line, dot_to_curve_line, sine_curve_line)
        self.wait(8.5)

        dot.remove_updater(go_around_circle)
