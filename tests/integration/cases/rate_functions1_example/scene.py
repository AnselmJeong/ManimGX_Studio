# Source: manim/utils/rate_functions.py
import manimgx as m


class RateFunctions1Example(m.Scene):
    def construct(self):
        line1 = m.Line(3 * m.LEFT, 3 * m.RIGHT).shift(m.UP).set_color(m.RED)
        line2 = m.Line(3 * m.LEFT, 3 * m.RIGHT).set_color(m.GREEN)
        line3 = m.Line(3 * m.LEFT, 3 * m.RIGHT).shift(m.DOWN).set_color(m.BLUE)

        dot1 = m.Dot().move_to(line1.get_left())
        dot2 = m.Dot().move_to(line2.get_left())
        dot3 = m.Dot().move_to(line3.get_left())

        label1 = m.Tex("Ease In").next_to(line1, m.RIGHT)
        label2 = m.Tex("Ease out").next_to(line2, m.RIGHT)
        label3 = m.Tex("Ease In Out").next_to(line3, m.RIGHT)

        self.play(
            m.FadeIn(m.VGroup(line1, line2, line3)),
            m.FadeIn(m.VGroup(dot1, dot2, dot3)),
            m.Write(m.VGroup(label1, label2, label3)),
        )
        self.play(
            m.MoveAlongPath(dot1, line1, rate_func=m.ease_in_sine),
            m.MoveAlongPath(dot2, line2, rate_func=m.ease_out_sine),
            m.MoveAlongPath(dot3, line3, rate_func=m.ease_in_out_sine),
            run_time=7,
        )
        self.wait()
