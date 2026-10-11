# Source: manim/mobject/mobject.py
import manimgx as m


class ArrangeInGrid(m.Scene):
    def construct(self):
        boxes = m.VGroup(
            *[
                m.Rectangle(m.WHITE, 0.5, 0.5).add(m.Text(str(i + 1)).scale(0.5))
                for i in range(24)
            ]
        )
        self.add(boxes)

        boxes.arrange_in_grid(
            buff=(0.25, 0.5),
            col_alignments="lccccr",
            row_alignments="uccd",
            col_widths=[1, *[None] * 4, 1],
            row_heights=[1, None, None, 1],
            flow_order="dr",
        )
        self.wait()
