import math

import manimgx as m

TERMS = 18


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.MathTex(
                "\\frac{\\pi}{2} = \\frac{2 \\cdot 2}{1 \\cdot 3} \\cdot \\frac{4"
                " \\cdot 4}{3 \\cdot 5} \\cdot \\frac{6 \\cdot 6}{5 \\cdot 7} \\cdots",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        line = m.NumberLine(
            x_range=[1.0, 1.8, 0.2],
            length=11,
            include_numbers=True,
        ).move_to(m.DOWN * 0.5)
        self.add(line)

        target_x = math.pi / 2
        target = m.DashedLine(
            line.n2p(target_x) + m.UP * 0.3,
            line.n2p(target_x) + m.DOWN * 0.3,
            color=m.YELLOW,
            stroke_width=3,
        )
        target_label = (
            m.MathTex(
                "\\pi/2 \\approx 1.5708",
                color=m.YELLOW,
            )
            .scale(0.55)
            .next_to(target, m.DOWN, buff=0.15)
        )
        self.play(m.Create(target), m.Write(target_label))

        product = 1.0
        prev_pt = None
        for n in range(1, TERMS + 1):
            product *= (2 * n) * (2 * n) / ((2 * n - 1) * (2 * n + 1))
            if not (1.0 <= product <= 1.8):
                continue
            pt = line.n2p(product)
            dot = m.Dot(pt, color=m.GREEN, radius=0.06)
            anims: list[m.Animation] = [m.FadeIn(dot, scale=0.5)]
            if prev_pt is not None:
                anims.append(
                    m.Create(m.Line(prev_pt, pt, color=m.GREEN, stroke_width=1.5)),
                )
            self.play(*anims, run_time=0.3)
            prev_pt = pt
        self.wait(1.5)
