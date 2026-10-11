# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class PolarPlaneGetAxesExample(m.Scene):
    def construct(self):
        pp = m.PolarPlane(size=6)
        axes_pair = pp.get_axes()
        assert len(list(axes_pair)) == 2
        self.add(pp)
        self.wait()
