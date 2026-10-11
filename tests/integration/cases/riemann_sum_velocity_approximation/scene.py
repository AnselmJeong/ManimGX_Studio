import math

import manimgx as m


def v(t: float) -> float:
    return 1.0 + 0.5 * math.sin(2 * t)


class TeacherScene(m.Scene):
    def construct(self) -> None:
        ax = m.Axes(
            x_range=[0, 4, 1],
            y_range=[0, 2, 0.5],
            x_length=10,
            y_length=5,
        ).shift(m.DOWN * 0.4)
        curve = ax.plot(v, color=m.BLUE, x_range=[0, 4])
        self.play(m.Create(ax), m.Create(curve))

        title = m.Tex(
            "Distance $\\approx \\sum v(t_i)\\, \\Delta t$",
        ).to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        dt = m.ValueTracker(1.0)

        def make_rects() -> m.VGroup:
            current_dt = dt.get_value()
            num = max(1, int(round(4.0 / current_dt)))
            actual_dt = 4.0 / num
            rects = m.VGroup()
            for i in range(num):
                t_i = i * actual_dt
                h = v(t_i)
                rect = m.Polygon(
                    ax.c2p(t_i, 0),
                    ax.c2p(t_i + actual_dt, 0),
                    ax.c2p(t_i + actual_dt, h),
                    ax.c2p(t_i, h),
                    color=m.YELLOW,
                    fill_color=m.YELLOW,
                    fill_opacity=0.4,
                    stroke_width=1,
                )
                rects.add(rect)
            return rects

        self.add(m.always_redraw(make_rects))
        self.wait(0.4)
        self.play(dt.animate.set_value(0.1), run_time=5.0)
        self.wait(1.5)
