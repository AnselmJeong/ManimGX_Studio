# Source: manim/mobject/opengl/opengl_mobject.py
import numpy as np

import manimgx as m


class ArrangeInGrid(m.Scene):
    def construct(self):
        # Add some numbered boxes:
        np.random.seed(3)
        boxes = m.VGroup(
            *[
                m.Rectangle(
                    m.WHITE,
                    np.random.random() + 0.5,
                    np.random.random() + 0.5,
                ).add(m.Text(str(i + 1)).scale(0.5))
                for i in range(22)
            ]
        )
        self.add(boxes)

        boxes.arrange_in_grid(
            buff=(0.25, 0.5),
            col_alignments="lccccr",
            row_alignments="uccd",
            col_widths=[2, *[None] * 4, 2],
            flow_order="dr",
        )
        self.wait()
