# Source: manim/mobject/geometry/arc.py
import manimgx as m


class CubicBezierAnchorHandleKwargs(m.Scene):
    def construct(self):
        bezier = m.CubicBezier(
            start_anchor=[-3.0, 0.0, 0.0],
            start_handle=[-1.0, 2.0, 0.0],
            end_handle=[1.0, -2.0, 0.0],
            end_anchor=[3.0, 0.0, 0.0],
            color=m.YELLOW,
            stroke_width=6,
        )
        self.add(bezier)
        self.wait()
