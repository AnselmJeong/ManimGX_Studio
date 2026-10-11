import math

import manimgx as m

TERMS = 15


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.MathTex(
                "\\sum_{n=1}^{\\infty} \\tfrac{1}{n^2} = \\tfrac{\\pi^2}{6} \\approx"
                " 1.6449",
            )
            .scale(0.95)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        line = m.NumberLine(
            x_range=[1.0, 1.7, 0.1],
            length=11,
            include_numbers=True,
        ).move_to(m.DOWN * 0.5)
        self.add(line)

        target = math.pi * math.pi / 6
        target_line = m.DashedLine(
            line.n2p(target) + m.UP * 0.3,
            line.n2p(target) + m.DOWN * 0.3,
            color=m.RED,
            stroke_width=3,
        )
        self.play(m.Create(target_line))

        partial = 0.0
        prev_pt = None
        for n in range(1, TERMS + 1):
            partial += 1.0 / (n * n)
            if not (1.0 <= partial <= 1.7):
                continue
            pt = line.n2p(partial)
            dot = m.Dot(pt, color=m.GREEN, radius=0.07)
            anims: list[m.Animation] = [m.FadeIn(dot, scale=0.5)]
            if prev_pt is not None:
                anims.append(
                    m.Create(m.Line(prev_pt, pt, color=m.GREEN, stroke_width=1.5)),
                )
            self.play(*anims, run_time=0.32)
            prev_pt = pt
        self.wait(1.5)
