import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Three ways to define an ellipse").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        col1_label = m.Tex("1. Stretched circle", color=m.BLUE).scale(0.6)
        col1_drawing = m.Ellipse(width=2.0, height=1.2, color=m.WHITE, stroke_width=2)
        col1 = (
            m.VGroup(col1_label, col1_drawing)
            .arrange(m.DOWN, buff=0.3)
            .shift(m.LEFT * 4)
        )

        col2_label = m.Tex("2. Focal sum", color=m.GREEN).scale(0.6)
        col2_ellipse = m.Ellipse(width=2.0, height=1.2, color=m.WHITE, stroke_width=2)
        col2_f1 = m.Dot(np.array([-0.8, 0.0, 0.0]), color=m.YELLOW, radius=0.06)
        col2_f2 = m.Dot(np.array([0.8, 0.0, 0.0]), color=m.YELLOW, radius=0.06)
        col2_drawing = m.VGroup(col2_ellipse, col2_f1, col2_f2)
        col2 = m.VGroup(col2_label, col2_drawing).arrange(m.DOWN, buff=0.3)

        col3_label = m.Tex("3. Cone slice", color=m.RED).scale(0.6)
        cone = m.Polygon(
            np.array([0.0, 1.0, 0.0]),
            np.array([-1.0, -1.0, 0.0]),
            np.array([1.0, -1.0, 0.0]),
            color=m.WHITE,
            stroke_width=2,
        )
        slice_ellipse = m.Ellipse(width=1.5, height=0.4, color=m.RED, stroke_width=2.5)
        col3_drawing = m.VGroup(cone, slice_ellipse)
        col3 = (
            m.VGroup(col3_label, col3_drawing)
            .arrange(m.DOWN, buff=0.3)
            .shift(m.RIGHT * 4)
        )

        self.play(m.FadeIn(col1))
        self.wait(0.3)
        self.play(m.FadeIn(col2))
        self.wait(0.3)
        self.play(m.FadeIn(col3))
        self.wait(2.0)
