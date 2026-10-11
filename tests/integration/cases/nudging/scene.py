# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class Nudging(m.Scene):
    def construct(self):
        def func(pos):
            return np.sin(pos[1] / 2) * m.RIGHT + np.cos(pos[0] / 2) * m.UP

        vector_field = m.ArrowVectorField(
            func, x_range=[-7, 7, 1], y_range=[-4, 4, 1], length_func=lambda x: x / 2
        )
        self.add(vector_field)
        circle = m.Circle(radius=2).shift(m.LEFT)
        self.add(circle.copy().set_color(m.GRAY))
        dot = m.Dot().move_to(circle)

        vector_field.nudge(circle, -2, 60, True)
        vector_field.nudge(dot, -2, 60)

        circle.add_updater(vector_field.get_nudge_updater(pointwise=True))
        dot.add_updater(vector_field.get_nudge_updater())
        self.add(circle, dot)
        self.wait(6)
