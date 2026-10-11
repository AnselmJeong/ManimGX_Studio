# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class SpawningAndFlowingArea(m.Scene):
    def construct(self):
        def func(pos):
            return np.sin(pos[0]) * m.UR + np.cos(pos[1]) * m.LEFT + pos / 5

        stream_lines = m.StreamLines(
            func,
            x_range=[-3, 3, 0.2],
            y_range=[-2, 2, 0.2],
            padding=1,
            virtual_time=0.6,
            max_anchors_per_line=3,
        )

        spawning_area = m.Rectangle(width=6, height=4)
        flowing_area = m.Rectangle(width=8, height=6)
        labels = [m.Tex("Spawning Area"), m.Tex("Flowing Area").shift(m.DOWN * 2.5)]
        for lbl in labels:
            lbl.add_background_rectangle(opacity=0.6, buff=0.05)

        self.add(stream_lines, spawning_area, flowing_area, *labels)
        self.wait()
