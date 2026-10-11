# Source: manim/mobject/mobject.py
import manimgx as m


class MatchPointsScene(m.Scene):
    def construct(self):
        circ = m.Circle(fill_color=m.RED, fill_opacity=0.8)
        square = m.Square(fill_color=m.BLUE, fill_opacity=0.2)
        self.add(circ)
        self.wait(0.5)
        self.play(circ.animate.match_points(square))
        self.wait(0.5)
