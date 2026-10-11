import math

import manimgx as m


class TeacherScene(m.MovingCameraScene):
    def construct(self) -> None:
        ax = m.Axes(
            x_range=[-2, 2, 1],
            y_range=[-2, 2, 0.5],
            x_length=10,
            y_length=8,
        )
        f_curve = ax.plot(lambda x: math.sin(x), color=m.BLUE, x_range=[-2, 2])
        g_curve = ax.plot(lambda x: x, color=m.YELLOW, x_range=[-2, 2])
        f_label = m.MathTex("\\sin x", color=m.BLUE).move_to(ax.c2p(1.7, 1.5))
        g_label = m.MathTex("x", color=m.YELLOW).move_to(ax.c2p(1.85, 1.85))
        self.add(ax, f_curve, g_curve, f_label, g_label)
        self.wait(0.4)

        self.play(
            self.camera.frame.animate.set(width=1.8).move_to(ax.c2p(0.0, 0.0)),
            run_time=3.0,
        )
        self.wait(0.4)

        ratio = (
            m.MathTex(
                "\\lim_{x \\to 0} \\frac{\\sin x}{x} = \\frac{f'(0)}{g'(0)} = 1",
            )
            .scale(0.18)
            .move_to(ax.c2p(0.0, 0.55))
        )
        self.play(m.Write(ratio))
        self.wait(2.0)
