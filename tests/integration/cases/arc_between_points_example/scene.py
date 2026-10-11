# Source: manim/mobject/geometry/arc.py
import manimgx as m


class ArcBetweenPointsExample(m.Scene):
    def construct(self):
        circle = m.Circle(radius=2, stroke_color=m.GREY)
        dot_1 = m.Dot(color=m.GREEN).move_to([2, 0, 0]).scale(0.5)
        dot_1_text = m.Tex("(2,0)").scale(0.5).next_to(dot_1, m.RIGHT).set_color(m.BLUE)
        dot_2 = m.Dot(color=m.GREEN).move_to([0, 2, 0]).scale(0.5)
        dot_2_text = m.Tex("(0,2)").scale(0.5).next_to(dot_2, m.UP).set_color(m.BLUE)
        arc = m.ArcBetweenPoints(start=2 * m.RIGHT, end=2 * m.UP, stroke_color=m.YELLOW)
        self.add(circle, dot_1, dot_2, dot_1_text, dot_2_text)
        self.play(m.Create(arc))
