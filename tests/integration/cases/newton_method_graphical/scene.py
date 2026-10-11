import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Newton's method on $P(x) = x^3 - 3x + 1$").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        axes = m.Axes(
            x_range=[-2.5, 2.5, 1],
            y_range=[-3, 3, 1],
            x_length=8.0,
            y_length=4.0,
            tips=False,
            axis_config={"include_numbers": True, "stroke_width": 1.5},
        ).shift(m.DOWN * 0.4)
        f = lambda x: x**3 - 3 * x + 1
        df = lambda x: 3 * x * x - 3
        curve = axes.plot(f, color=m.BLUE, x_range=[-2.3, 2.3])
        self.play(m.Create(axes), m.Create(curve))

        x = 1.8
        prev_dot = None
        for _ in range(4):
            y = f(x)
            slope = df(x)
            x_new = x - y / slope
            tangent_x_start = max(x - 1.5, -2.4)
            tangent_x_end = min(x + 1.5, 2.4)
            tangent_pts = [
                axes.coords_to_point(tx, y + slope * (tx - x))
                for tx in [tangent_x_start, tangent_x_end]
            ]
            tangent = m.Line(
                tangent_pts[0], tangent_pts[1], color=m.YELLOW, stroke_width=2.0
            )

            dot = m.Dot(axes.coords_to_point(x, y), color=m.RED, radius=0.07)
            xnew_dot = m.Dot(axes.coords_to_point(x_new, 0), color=m.GREEN, radius=0.07)
            drop = m.DashedLine(
                axes.coords_to_point(x_new, 0),
                axes.coords_to_point(x_new, f(x_new)),
                color=m.GREEN,
                stroke_width=1.5,
            )

            self.play(m.FadeIn(dot), m.Create(tangent), run_time=0.6)
            self.play(m.FadeIn(xnew_dot), m.Create(drop), run_time=0.4)
            x = x_new

        self.wait(1.5)
