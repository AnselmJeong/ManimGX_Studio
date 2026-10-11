# Source: manim/animation/growing.py
import manimgx as m


class Growing(m.Scene):
    def construct(self):
        square = m.Square()
        circle = m.Circle()
        triangle = m.Triangle()
        arrow = m.Arrow(m.LEFT, m.RIGHT)
        star = m.Star()

        m.VGroup(square, circle, triangle).set_x(0).arrange(buff=1.5).set_y(2)
        m.VGroup(arrow, star).move_to(m.DOWN).set_x(0).arrange(buff=1.5).set_y(-2)

        self.play(m.GrowFromPoint(square, m.ORIGIN))
        self.play(m.GrowFromCenter(circle))
        self.play(m.GrowFromEdge(triangle, m.DOWN))
        self.play(m.GrowArrow(arrow))
        self.play(m.SpinInFromNothing(star))
