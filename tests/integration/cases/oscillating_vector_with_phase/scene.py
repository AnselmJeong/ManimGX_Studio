import math
from collections.abc import Callable

import manimgx as m

CONFIGS = [
    (-3.5, 0.0, m.YELLOW),
    (0.0, math.pi / 2, m.GREEN),
    (3.5, math.pi, m.RED),
]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Three vectors oscillating with different phases",
            )
            .scale(0.8)
            .to_edge(m.UP, buff=0.4)
        )
        self.play(m.Write(title))

        t = m.ValueTracker(0.0)

        def make_arrow(
            origin_x: float, phase: float, color: str
        ) -> Callable[[], m.Arrow]:
            def factory() -> m.Arrow:
                amp = 2.0 * math.sin(t.get_value() + phase)
                start = [origin_x, -1.0, 0]
                end = [origin_x, -1.0 + amp, 0]
                return m.Arrow(start, end, color=color, buff=0, stroke_width=6)

            return factory

        for ox, ph, color in CONFIGS:
            self.add(m.always_redraw(make_arrow(ox, ph, color)))

        self.play(t.animate.set_value(4 * math.pi), run_time=5.0, rate_func=m.linear)
        self.wait(1.0)
