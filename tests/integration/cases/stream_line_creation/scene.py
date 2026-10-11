# Source: manim/mobject/vector_field.py
import random

import manimgx as m


class StreamLineCreation(m.Scene):
    def construct(self):
        func = lambda pos: (pos[0] * m.UR + pos[1] * m.LEFT) - pos
        stream_lines = m.StreamLines(
            func,
            color=m.YELLOW,
            x_range=[-7, 7, 1],
            y_range=[-4, 4, 1],
            stroke_width=3,
            virtual_time=1,  # use shorter lines
            max_anchors_per_line=6,  # better performance with fewer anchors
        )
        random.seed(0)
        self.play(stream_lines.create())  # uses virtual_time as run_time
        self.wait()
