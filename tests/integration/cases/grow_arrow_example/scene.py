# Source: manim/animation/growing.py
import manimgx as m


class GrowArrowExample(m.Scene):
    def construct(self):
        arrows = [
            m.Arrow(2 * m.LEFT, 2 * m.RIGHT),
            m.Arrow(2 * m.DR, 2 * m.UL),
        ]
        m.VGroup(*arrows).set_x(0).arrange(buff=2)
        self.play(m.GrowArrow(arrows[0]))
        self.play(m.GrowArrow(arrows[1], point_color=m.RED))
