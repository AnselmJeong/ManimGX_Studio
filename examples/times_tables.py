"""Times tables on a circle.

Put 200 points around a circle, numbered 0 to 199, and join each point n to the point k·n,
counting around the circle (mod 200). For k = 2 the lines wrap a cardioid, the heart traced by
a point on a circle rolling around another of the same size; for k = 3, a nephroid, with two
lobes; for k, a curve with k − 1 lobes. Let k grow continuously and the figure turns, splits
and folds from one curve into the next.
"""

import numpy as np

import manimgx as m

WALL = 3.2  # the README wall's 5 seconds start here
POINTS = 200
RADIUS = 3.45


def on_circle(angle: np.ndarray) -> np.ndarray:
    return RADIUS * np.stack(
        [np.cos(angle), np.sin(angle), np.zeros_like(angle)], axis=-1
    )


class TimesTables(m.Scene):
    def construct(self) -> None:
        k = m.ValueTracker(2.0)
        n = np.arange(POINTS)
        start = np.pi + m.TAU * n / POINTS  # point 0 on the left, as in a clock turned
        colors = m.color_gradient(
            [m.BLUE, m.TEAL, m.GREEN, m.YELLOW, m.RED, m.PURPLE, m.BLUE], POINTS
        )
        chords = m.VGroup(
            *(
                m.Line(m.LEFT, m.RIGHT, stroke_width=2, stroke_opacity=0.75, color=c)
                for c in colors
            )
        )

        def draw(group: m.VGroup) -> None:
            ends = on_circle(np.pi + m.TAU * k.get_value() * n / POINTS)
            begins = on_circle(start)
            for line, a, b in zip(group, begins, ends, strict=True):
                assert isinstance(line, m.Line)
                line.set_points_as_corners([a, b])

        chords.add_updater(draw)
        draw(chords)
        ring = m.Circle(radius=RADIUS, stroke_color=m.GREY_B, stroke_width=3)
        dots = m.VGroup(
            *(m.Dot(p, radius=0.022, color=m.GREY_A) for p in on_circle(start))
        )

        rule = m.MathTex(r"n \mapsto k \cdot n \pmod{200}", font_size=46)
        value = m.DecimalNumber(2.0, num_decimal_places=2, font_size=60, color=m.YELLOW)
        k_label = m.MathTex("k =", font_size=60)
        readout = m.VGroup(k_label, value).arrange(m.RIGHT, buff=0.2)
        panel = m.VGroup(rule, readout).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.35)
        panel.to_corner(m.UL, buff=0.5)
        value.add_updater(lambda d: d.set_value(k.get_value()))

        names = {2: "cardioid", 3: "nephroid", 4: "three lobes", 5: "four lobes"}
        name = m.Tex(names[2], font_size=48, color=m.GREY_A).next_to(
            panel, m.DOWN, aligned_edge=m.LEFT, buff=0.4
        )

        self.play(m.Create(ring), m.FadeIn(dots), run_time=1)
        self.play(m.Create(chords, lag_ratio=0.01), m.Write(panel), run_time=1.8)
        self.play(m.FadeIn(name), run_time=0.4)
        for target in (3, 4, 5):
            self.play(
                k.animate.set_value(target),
                m.FadeOut(name),
                run_time=2.4,
            )
            name = m.Tex(names[target], font_size=48, color=m.GREY_A).move_to(
                name, aligned_edge=m.LEFT
            )
            self.play(m.FadeIn(name), run_time=0.4)
            self.wait(0.6)
        self.play(m.FadeOut(name), run_time=0.3)
        # then on, without stopping: the figures between and beyond
        self.play(k.animate.set_value(34), run_time=12, rate_func=m.linear)
        self.wait(1)


if __name__ == "__main__":
    TimesTables().render("times_tables.mp4")
