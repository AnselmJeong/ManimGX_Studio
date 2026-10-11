"""Show me the diagram that says 'Laplace turns derivatives into multiplication by s' - four corners, four arrows."""

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        top_left = m.MathTex(R"f(t)").scale(1.1)
        top_right = m.MathTex(R"F(s)").scale(1.1)
        bot_left = m.MathTex(R"f'(t)").scale(1.1)
        bot_right = m.MathTex(R"s F(s) - f(0)").scale(1.1)

        corners = m.VGroup(top_left, top_right, bot_left, bot_right)
        corners.arrange_in_grid(rows=2, cols=2, buff=2.0)

        top_arrow = m.Arrow(
            top_left.get_right(),
            top_right.get_left(),
            buff=0.25,
            color=m.YELLOW,
        )
        bot_arrow = m.Arrow(
            bot_left.get_right(),
            bot_right.get_left(),
            buff=0.25,
            color=m.YELLOW,
        )
        left_arrow = m.Arrow(
            top_left.get_bottom(),
            bot_left.get_top(),
            buff=0.25,
            color=m.TEAL,
        )
        right_arrow = m.Arrow(
            top_right.get_bottom(),
            bot_right.get_top(),
            buff=0.25,
            color=m.TEAL,
        )

        top_label = (
            m.MathTex(R"\mathcal{L}").scale(0.8).next_to(top_arrow, m.UP, buff=0.1)
        )
        (m.MathTex(R"\mathcal{L}").scale(0.8).next_to(bot_arrow, m.UP, buff=0.1))
        left_label = (
            m.MathTex(R"\tfrac{d}{dt}")
            .scale(0.8)
            .next_to(left_arrow, m.LEFT, buff=0.15)
        )
        right_label = (
            m.MathTex(R"\times s").scale(0.8).next_to(right_arrow, m.RIGHT, buff=0.15)
        )

        self.play(m.Write(top_left), run_time=0.8)
        self.play(m.GrowArrow(top_arrow), m.Write(top_label), run_time=0.8)
        self.play(
            m.TransformFromCopy(top_left, top_right),
            run_time=1.2,
        )
        self.play(m.GrowArrow(left_arrow), m.Write(left_label), run_time=0.8)
        self.play(
            m.TransformFromCopy(top_left, bot_left),
            run_time=1.2,
        )
        self.play(m.GrowArrow(right_arrow), m.Write(right_label), run_time=0.8)
        self.play(
            m.TransformFromCopy(bot_left, bot_right),
            run_time=1.2,
        )
        self.wait(1.0)
        self.wait(0.5)
