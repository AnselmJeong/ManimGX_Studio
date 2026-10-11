"""A secant becomes a tangent; VALUE selects the point on y = x²."""

import manimgx as m

VALUE = 1.0
PACE = 1.0


class Lesson(m.Scene):
    def construct(self) -> None:
        m.config.background_color = "#101825"
        title = m.Text("미분: 순간의 기울기", font_size=36).to_edge(m.UP, buff=0.4)
        axes = m.Axes(
            x_range=[-0.5, 3.5, 1],
            y_range=[-1, 10, 2],
            x_length=7.4,
            y_length=4.6,
            tips=False,
        ).shift(m.LEFT * 1.6)
        axes.add_coordinates()
        curve = axes.plot(lambda x: x * x, x_range=[0, 3], color=m.BLUE)
        equation = m.MathTex(r"f(x)=x^2", font_size=38).move_to([4.3, 1.5, 0])
        caption = m.Text(
            "두 점을 잇는 직선의 기울기를 관찰합니다", font_size=24
        ).to_edge(m.DOWN)
        self.play(m.Write(title), m.Create(axes), run_time=1.2 * PACE)
        self.play(
            m.Create(curve), m.Write(equation), m.FadeIn(caption), run_time=1.5 * PACE
        )
        x = VALUE
        h = m.ValueTracker(1.0)
        fixed = m.Dot(axes.c2p(x, x * x), color=m.YELLOW)
        moving = m.always_redraw(
            lambda: m.Dot(
                axes.c2p(x + h.get_value(), (x + h.get_value()) ** 2), color=m.TEAL
            )
        )

        def secant() -> m.Line:
            slope = 2 * x + h.get_value()
            return m.Line(
                axes.c2p(x - 0.65, x * x - 0.65 * slope),
                axes.c2p(x + 1.1, x * x + 1.1 * slope),
                color=m.YELLOW,
                stroke_width=4,
            )

        line = m.always_redraw(secant)
        ratio = m.MathTex(r"\frac{\Delta y}{\Delta x}", font_size=42).move_to(
            [4.3, 0.2, 0]
        )
        self.play(
            m.FadeIn(fixed),
            m.FadeIn(moving),
            m.Create(line),
            m.Write(ratio),
            run_time=1.2 * PACE,
        )
        self.wait(1 * PACE)
        next_caption = m.Text(
            "두 점이 가까워지면, 할선은 접선에 다가갑니다", font_size=24
        ).to_edge(m.DOWN)
        self.play(m.Transform(caption, next_caption), run_time=0.5 * PACE)
        self.play(h.animate.set_value(0.01), run_time=4.5 * PACE, rate_func=m.smooth)
        result = m.MathTex(r"f'(x)=2x", font_size=42).move_to([4.3, -1.15, 0])
        number = m.Text(f"x = {x:g} 에서 기울기 = {2 * x:g}", font_size=23).move_to(
            [3.9, -2.0, 0]
        )
        final_caption = m.Text(
            "미분은 한 점에서의 순간 변화율입니다", font_size=24
        ).to_edge(m.DOWN)
        self.play(
            m.Write(result),
            m.FadeIn(number),
            m.Transform(caption, final_caption),
            run_time=1.3 * PACE,
        )
        self.wait(2.5 * PACE)
