import math

import manimgx as m


def taylor_exp(x: float, n: int) -> float:
    return float(sum(x**k / math.factorial(k) for k in range(n + 1)))


def taylor_label_text(n: int) -> str:
    parts = ["1"]
    if n >= 1:
        parts.append("x")
    for k in range(2, n + 1):
        parts.append(f"\\tfrac{{x^{{{k}}}}}{{{k}!}}")
    return "+".join(parts)


class TeacherScene(m.Scene):
    def construct(self) -> None:
        ax = m.Axes(
            x_range=[-2, 2, 1],
            y_range=[-1, 6, 1],
            x_length=10,
            y_length=6,
        )
        true_curve = ax.plot(lambda x: math.exp(x), color=m.BLUE, x_range=[-2, 2])
        true_label = m.MathTex("e^x", color=m.BLUE).to_corner(m.UR, buff=0.5)
        self.play(m.Create(ax), m.Create(true_curve), m.Write(true_label))

        approx = None
        approx_label = None
        for n in range(1, 7):
            new_approx = ax.plot(
                lambda x, n=n: taylor_exp(x, n),
                color=m.YELLOW,
                x_range=[-2, 2],
            )
            new_label = (
                m.MathTex(
                    "\\approx " + taylor_label_text(n),
                    color=m.YELLOW,
                )
                .scale(0.55)
                .to_corner(m.UR, buff=0.5)
                .shift(m.DOWN * 0.65)
            )

            if approx is None or approx_label is None:
                approx, approx_label = new_approx, new_label
                self.play(m.Create(approx), m.Write(approx_label))
            else:
                self.play(
                    m.Transform(approx, new_approx),
                    m.Transform(approx_label, new_label),
                    run_time=0.9,
                )
            self.wait(0.4)
        self.wait(1.5)
