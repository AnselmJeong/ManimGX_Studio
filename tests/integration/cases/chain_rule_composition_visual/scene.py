import math

import manimgx as m


def g(x: float) -> float:
    return x * x


def f(y: float) -> float:
    return math.sin(y)


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.MathTex(
            "\\frac{d}{dx} f(g(x)) = f'(g(x)) \\cdot g'(x)",
            color=m.YELLOW,
        ).to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        x_line = m.NumberLine(
            x_range=[0, 3, 1],
            length=9,
            include_numbers=True,
        ).move_to(m.UP * 1.0)
        g_line = m.NumberLine(
            x_range=[0, 9, 2],
            length=9,
            include_numbers=True,
        ).move_to(m.DOWN * 0.5)
        f_line = m.NumberLine(
            x_range=[-1, 1, 0.5],
            length=9,
            include_numbers=True,
        ).move_to(m.DOWN * 2.1)
        x_label = m.MathTex("x").scale(0.8).next_to(x_line, m.LEFT, buff=0.3)
        g_label = m.MathTex("g(x) = x^2").scale(0.7).next_to(g_line, m.LEFT, buff=0.3)
        f_label = (
            m.MathTex("f(g(x)) = \\sin(x^2)")
            .scale(0.65)
            .next_to(f_line, m.LEFT, buff=0.3)
        )

        self.play(m.Create(x_line), m.Write(x_label))
        self.play(m.Create(g_line), m.Write(g_label))
        self.play(m.Create(f_line), m.Write(f_label))

        t = m.ValueTracker(0.4)
        x_dot = m.always_redraw(
            lambda: m.Dot(x_line.n2p(t.get_value()), color=m.YELLOW, radius=0.1),
        )
        g_dot = m.always_redraw(
            lambda: m.Dot(g_line.n2p(g(t.get_value())), color=m.YELLOW, radius=0.1),
        )
        f_dot = m.always_redraw(
            lambda: m.Dot(f_line.n2p(f(g(t.get_value()))), color=m.YELLOW, radius=0.1),
        )
        self.add(x_dot, g_dot, f_dot)

        self.play(t.animate.set_value(2.6), run_time=4.0)
        self.wait(1.5)
