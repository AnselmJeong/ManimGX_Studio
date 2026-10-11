"""Show the integral of x^2 from 0 to 2 as a Riemann sum, refining dx from coarse to fine."""

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self):
        axes = m.Axes(
            x_range=(0.0, 2.5, 0.5),
            y_range=(0.0, 5.0, 1.0),
            x_length=9.0,
            y_length=5.0,
        )
        curve = axes.plot(lambda x: x**2, x_range=(0.0, 2.0), color=m.YELLOW)

        coarse = axes.get_riemann_rectangles(
            curve,
            x_range=(0.0, 2.0),
            dx=0.5,
            color=(m.TEAL, m.BLUE_B, m.DARK_BLUE),
        )
        fine = axes.get_riemann_rectangles(
            curve,
            x_range=(0.0, 2.0),
            dx=0.1,
            color=(m.TEAL, m.BLUE_B, m.DARK_BLUE),
        )

        self.play(m.Create(axes), run_time=1.0)
        self.play(m.Create(curve), run_time=1.5)
        self.play(m.Create(coarse), run_time=1.5)
        self.wait(0.5)
        self.play(m.ReplacementTransform(coarse, fine), run_time=3.0)
        self.wait(0.5)
