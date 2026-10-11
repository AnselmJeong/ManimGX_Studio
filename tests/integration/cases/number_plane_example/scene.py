# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class NumberPlaneExample(m.Scene):
    def construct(self):
        number_plane = m.NumberPlane(
            background_line_style={
                "stroke_color": m.TEAL,
                "stroke_width": 4,
                "stroke_opacity": 0.6,
            }
        )
        self.add(number_plane)
        self.wait()
