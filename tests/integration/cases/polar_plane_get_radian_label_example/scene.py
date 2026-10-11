# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class PolarPlaneGetRadianLabelExample(m.Scene):
    def construct(self):
        pp = m.PolarPlane(size=4, azimuth_units="PI radians")
        label_q = pp.get_radian_label(0.25)
        self.add(pp, label_q)
        self.wait()
