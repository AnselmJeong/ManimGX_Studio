# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class PointsAsCornersExample(m.Scene):
    def construct(self):
        corners = (
            # create square
            m.UR,
            m.UL,
            m.DL,
            m.DR,
            m.UR,
            # create crosses
            m.DL,
            m.UL,
            m.DR,
        )
        vmob = m.VMobject(stroke_color=m.RED)
        vmob.set_points_as_corners(corners).scale(2)
        self.add(vmob)
        self.wait()
