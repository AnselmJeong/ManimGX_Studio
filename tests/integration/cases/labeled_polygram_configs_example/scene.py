# Source: manim/mobject/geometry/labeled.py
import manimgx as m


class LabeledPolygramConfigsExample(m.Scene):
    def construct(self):
        polygram = m.LabeledPolygram(
            [[-2.0, -1.0, 0.0], [2.0, -1.0, 0.0], [0.0, 2.0, 0.0]],
            label="X",
            label_config={"font_size": 36, "color": m.WHITE},
            box_config={"color": m.BLUE_E, "buff": 0.1, "fill_opacity": 0.9},
            frame_config={"color": m.YELLOW, "stroke_width": 2, "buff": 0.1},
            color=m.GREY_C,
            fill_opacity=0.4,
            stroke_width=4,
        )
        self.add(polygram)
        self.wait()
