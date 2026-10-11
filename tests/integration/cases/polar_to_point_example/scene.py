# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class PolarToPointExample(m.Scene):
    def construct(self):
        polarplane_pi = m.PolarPlane(azimuth_units="PI radians", size=6)
        polartopoint_vector = m.Vector(polarplane_pi.polar_to_point(3, m.PI / 4))
        self.add(polarplane_pi)
        self.add(polartopoint_vector)
        self.wait()
