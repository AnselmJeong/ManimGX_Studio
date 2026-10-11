# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class NumberPlaneScaled(m.Scene):
    def construct(self):
        number_plane = m.NumberPlane(
            x_range=(-4, 11, 1),
            y_range=(-3, 3, 1),
            x_length=5,
            y_length=2,
        ).move_to(m.LEFT * 3)

        number_plane_scaled_y = m.NumberPlane(
            x_range=(-4, 11, 1),
            x_length=5,
            y_length=4,
        ).move_to(m.RIGHT * 3)

        self.add(number_plane)
        self.add(number_plane_scaled_y)
        self.wait()
