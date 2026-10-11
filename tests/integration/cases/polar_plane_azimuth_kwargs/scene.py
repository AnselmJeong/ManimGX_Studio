# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class PolarPlaneAzimuthKwargsExample(m.Scene):
    def construct(self):
        pp = m.PolarPlane(
            size=5,
            azimuth_units="PI radians",
            azimuth_compact_fraction=False,
            azimuth_offset=m.PI / 12,
            azimuth_direction="CW",
            azimuth_label_buff=0.15,
            faded_line_ratio=2,
            background_line_style={"stroke_width": 2.5},
            faded_line_style={"stroke_width": 0.75, "stroke_opacity": 0.4},
        ).add_coordinates()
        self.add(pp)
        self.wait()
