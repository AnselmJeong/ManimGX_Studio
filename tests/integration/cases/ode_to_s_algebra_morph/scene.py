"""Show the Laplace transform of the ODE m*x'' + mu*x' + k*x = 0 turning into the algebraic equation in s."""

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "key_map kwarg unavailable in manimgx - substituted with shared {{token}} markers "
    "and unmatched-fade behavior"
)


class TeacherScene(m.Scene):
    def construct(self):
        top_strip = m.Rectangle(width=12.0, height=2.0, color=m.BLUE).set_fill(
            m.BLUE, opacity=0.12
        )
        bot_strip = m.Rectangle(width=12.0, height=2.0, color=m.TEAL).set_fill(
            m.TEAL, opacity=0.12
        )
        top_strip.move_to(2.0 * m.UP)
        bot_strip.move_to(2.0 * m.DOWN)

        top_label = m.Text("Time domain", font_size=24).next_to(
            top_strip, m.UP, buff=0.1
        )
        bot_label = m.Text("s domain", font_size=24).next_to(
            bot_strip, m.DOWN, buff=0.1
        )

        time_eq = m.MathTex(
            "{{m}}",
            R"\, x''(t) + ",
            R"{{\mu}}",
            R"\, x'(t) + ",
            "{{k}}",
            R"\, x(t) ",
            "{{=}}",
            " ",
            "{{0}}",
        ).scale(1.1)
        time_eq.move_to(top_strip.get_center())

        s_eq = m.MathTex(
            "{{m}}",
            R" s^2 X(s) + ",
            R"{{\mu}}",
            R" s X(s) + ",
            "{{k}}",
            R" X(s) ",
            "{{=}}",
            " ",
            "{{0}}",
        ).scale(1.1)
        s_eq.move_to(bot_strip.get_center())

        arrow = m.Arrow(
            top_strip.get_bottom(),
            bot_strip.get_top(),
            buff=0.15,
            color=m.YELLOW,
        )
        arrow_label = (
            m.MathTex(R"\mathcal{L}").scale(0.9).next_to(arrow, m.RIGHT, buff=0.15)
        )

        self.play(
            m.Create(top_strip),
            m.Create(bot_strip),
            run_time=1.0,
        )
        self.play(
            m.Write(top_label),
            m.Write(bot_label),
            run_time=0.8,
        )
        self.play(m.Write(time_eq), run_time=2.0)
        self.play(
            m.GrowArrow(arrow),
            m.Write(arrow_label),
            run_time=0.8,
        )
        self.play(
            m.TransformMatchingTex(time_eq, s_eq),
            run_time=3.0,
        )
        self.wait(1.0)
        self.wait(0.5)
