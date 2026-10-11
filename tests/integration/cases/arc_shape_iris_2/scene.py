# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class ArcShapeIris(m.Scene):
    def construct(self):
        colors = [
            m.DARK_BROWN,
            m.BLUE_E,
            m.BLUE_D,
            m.BLUE_A,
            m.TEAL_B,
            m.GREEN_B,
            m.YELLOW_E,
        ]
        radius = [1 + rad * 0.1 for rad in range(len(colors))]

        circles_group = m.VGroup()

        # zip(radius, color) makes the iterator [(radius[i], color[i]) for i in range(radius)]
        circles_group.add(
            *[
                m.Circle(radius=rad, stroke_width=10, color=col)
                for rad, col in zip(radius, colors)
            ]
        )
        self.add(circles_group)
        self.wait()
