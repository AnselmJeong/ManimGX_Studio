import math

import numpy as np

import manimgx as m


def f(x: float) -> float:
    return math.sin(x)


def f_pp(x: float) -> float:
    return -math.sin(x)


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "$f''(x)$: curvature drives heat flow",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        ax = m.Axes(
            x_range=[-math.pi, math.pi, math.pi / 2],
            y_range=[-1.5, 1.5, 0.5],
            x_length=11,
            y_length=5,
        ).shift(m.DOWN * 0.3)
        curve = ax.plot(f, color=m.BLUE, x_range=[-math.pi, math.pi])
        self.add(ax, curve)

        arrows = m.VGroup()
        for x in np.linspace(-math.pi + 0.3, math.pi - 0.3, 14):
            y = f(x)
            fpp = f_pp(x)
            arrow_len = 0.5 * fpp
            color = m.GREEN if fpp > 0 else m.RED
            start = ax.c2p(x, y)
            end = ax.c2p(x, y + arrow_len)
            arrows.add(
                m.Arrow(
                    start,
                    end,
                    color=color,
                    buff=0,
                    stroke_width=2.5,
                    max_tip_length_to_length_ratio=0.4,
                ),
            )
        self.play(
            m.LaggedStart(*[m.GrowArrow(a) for a in arrows], lag_ratio=0.05),
            run_time=2.5,
        )
        self.wait(2.0)
