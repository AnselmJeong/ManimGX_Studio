# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class ContinuousMotion(m.Scene):
    def construct(self):
        def func(pos):
            return np.sin(pos[0] / 2) * m.UR + np.cos(pos[1] / 2) * m.LEFT

        stream_lines = m.StreamLines(func, stroke_width=3, max_anchors_per_line=7)
        self.add(stream_lines)
        stream_lines.start_animation(warm_up=False, flow_speed=1.5)
        self.wait(stream_lines.virtual_time / stream_lines.flow_speed)
