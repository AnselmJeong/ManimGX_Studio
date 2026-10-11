# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class PolarPlaneAddCoordinatesArgsExample(m.Scene):
    def construct(self):
        pp = m.PolarPlane(size=5, azimuth_units="PI radians")
        pp.add_coordinates(r_values=[1, 2], a_values=[0.0, 0.25, 0.5, 0.75])
        self.add(pp)
        self.wait()
