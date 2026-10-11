# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class CutoutMainShapeKwarg(m.Scene):
    def construct(self):
        outer = m.Square(side_length=3.0)
        hole = m.Circle(radius=0.6)
        cut = m.Cutout(main_shape=outer, fill_opacity=1.0, color=m.BLUE)
        cut.add(hole)
        # Build a second cutout via positional + keyword mix to keep the
        # missing-list ``main_shape=`` signature alive on the scene path.
        outer_b = m.Square(side_length=1.5).shift(m.DOWN * 2)
        cut_b = m.Cutout(main_shape=outer_b, color=m.YELLOW, fill_opacity=0.8)
        self.add(cut, cut_b)
        self.wait()
