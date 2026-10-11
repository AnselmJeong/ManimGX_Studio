# Source: manim/mobject/geometry/line.py
import manimgx as m


class DoubleArrowExample2(m.Scene):
    def construct(self):
        box = m.Square()
        p1 = box.get_left()
        p2 = box.get_right()
        d1 = m.DoubleArrow(p1, p2, buff=0)
        d2 = m.DoubleArrow(p1, p2, buff=0, tip_length=0.2, color=m.YELLOW)
        d3 = m.DoubleArrow(p1, p2, buff=0, tip_length=0.4, color=m.BLUE)
        m.Group(d1, d2, d3).arrange(m.DOWN)
        self.add(box, d1, d2, d3)
        self.wait()
