# Source: manim/mobject/geometry/labeled.py
import manimgx as m


class LabeledLineExample(m.Scene):
    def construct(self):
        line = m.LabeledLine(
            label="0.5",
            label_position=0.8,
            label_config={"font_size": 20},
            start=m.LEFT + m.DOWN,
            end=m.RIGHT + m.UP,
        )

        line.set_length(line.get_length() * 2)
        self.add(line)
        self.wait()
