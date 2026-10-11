from fractions import Fraction

import numpy as np

import manimgx as m

DENOMS = list(range(2, 30))


class TeacherScene(m.Scene):
    def construct(self) -> None:
        line = m.NumberLine(
            x_range=[0, 1, 0.5],
            length=12,
            include_numbers=True,
            numbers_to_include=[0, 1],
        )
        self.add(line)

        title = m.Tex(
            "Rationals are ",
            "dense",
            " in ",
            "$[0, 1]$",
        ).to_edge(m.UP)
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        seen: set[Fraction] = set()
        ticks = m.VGroup()
        for d in DENOMS:
            for n in range(1, d):
                f = Fraction(n, d)
                if f in seen:
                    continue
                seen.add(f)
                val = float(f)
                tick_height = 0.35 / d
                tick = m.Line(
                    line.n2p(val) + m.UP * tick_height,
                    line.n2p(val) + m.DOWN * tick_height,
                    color=m.YELLOW,
                    stroke_width=1.5,
                )
                ticks.add(tick)
        self.play(m.Create(ticks, lag_ratio=0.0), run_time=2.5)
        self.wait(0.4)

        covers = [(0.5, 0.12), (0.2, 0.06), (0.7, 0.03)]
        intervals = m.VGroup()
        for center, width in covers:
            left = line.n2p(center - width / 2)
            right = line.n2p(center + width / 2)
            rect = m.Rectangle(
                width=float(np.linalg.norm(right - left)),
                height=0.32,
                color=m.BLUE,
                fill_color=m.BLUE,
                fill_opacity=0.35,
                stroke_width=1.5,
            ).move_to((left + right) / 2)
            intervals.add(rect)

        self.play(
            m.LaggedStart(*[m.FadeIn(r) for r in intervals], lag_ratio=0.25),
            run_time=1.5,
        )
        self.wait(1.5)

        caption = m.Tex(
            "...yet they have ",
            "measure 0",
        ).next_to(line, m.DOWN, buff=1.6)
        caption[1].set_color(m.RED)
        self.play(m.Write(caption))
        self.wait(2.0)
