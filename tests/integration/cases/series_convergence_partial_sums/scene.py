import math

import manimgx as m

TERMS = 14


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.MathTex(
            "\\frac{\\pi}{4} = 1 - \\frac{1}{3} + \\frac{1}{5} - \\frac{1}{7} +"
            " \\cdots",
        ).to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        line = m.NumberLine(
            x_range=[0, 1, 0.25],
            length=11,
            include_numbers=True,
        ).move_to(m.DOWN * 0.4)
        self.add(line)

        target_x = math.pi / 4
        target = m.DashedLine(
            line.n2p(target_x) + m.UP * 0.3,
            line.n2p(target_x) + m.DOWN * 0.3,
            color=m.YELLOW,
            stroke_width=3,
        )
        target_label = (
            m.MathTex(
                "\\pi/4 \\approx 0.785",
                color=m.YELLOW,
            )
            .scale(0.55)
            .next_to(target, m.DOWN, buff=0.15)
        )
        self.play(m.Create(target), m.Write(target_label))

        partial = 0.0
        prev_pt = None
        for k in range(TERMS):
            partial += ((-1) ** k) / (2 * k + 1)
            pt = line.n2p(partial)
            dot = m.Dot(pt, color=m.GREEN, radius=0.06)
            elems: list[m.Animation] = [m.FadeIn(dot, scale=0.5)]
            if prev_pt is not None:
                elems.append(
                    m.Create(
                        m.Line(prev_pt, pt, color=m.GREEN, stroke_width=1.5),
                    )
                )
            self.play(*elems, run_time=0.32)
            prev_pt = pt
        self.wait(1.5)
