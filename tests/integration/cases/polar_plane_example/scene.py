# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class PolarPlaneExample(m.Scene):
    def construct(self):
        polarplane_pi = m.PolarPlane(
            azimuth_units="PI radians",
            size=6,
            azimuth_label_font_size=33.6,
            radius_config={"font_size": 33.6},
        ).add_coordinates()
        self.add(polarplane_pi)
        self.wait()
