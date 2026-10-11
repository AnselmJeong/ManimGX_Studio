# Source: manim/mobject/geometry/labeled.py
import manimgx as m


class LabelExample(m.Scene):
    def construct(self):
        label = m.Label(
            label=m.Text("Label Text", font="sans-serif"),
            box_config={"color": m.BLUE, "fill_opacity": 0.75},
        )
        label.scale(3)
        self.add(label)
        self.wait()
