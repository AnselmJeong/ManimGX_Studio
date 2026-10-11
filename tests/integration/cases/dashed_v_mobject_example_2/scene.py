# Source: manim/mobject/types/vectorized_mobject.py
import numpy as np

import manimgx as m


class DashedVMobjectExample(m.Scene):
    def construct(self):
        r = 0.5

        top_row = m.VGroup()  # Increasing num_dashes
        for dashes in range(1, 12):
            circ = m.DashedVMobject(
                m.Circle(radius=r, color=m.WHITE), num_dashes=dashes
            )
            top_row.add(circ)

        middle_row = m.VGroup()  # Increasing dashed_ratio
        for ratio in np.arange(1 / 11, 1, 1 / 11):
            circ = m.DashedVMobject(
                m.Circle(radius=r, color=m.WHITE), dashed_ratio=ratio
            )
            middle_row.add(circ)

        func1 = m.FunctionGraph(lambda t: t**5, [-1, 1], color=m.WHITE)
        func_even = m.DashedVMobject(func1, num_dashes=6, equal_lengths=True)
        func_stretched = m.DashedVMobject(func1, num_dashes=6, equal_lengths=False)
        bottom_row = m.VGroup(func_even, func_stretched)

        top_row.arrange(buff=0.3)
        middle_row.arrange()
        bottom_row.arrange(buff=1)
        everything = m.VGroup(top_row, middle_row, bottom_row).arrange(m.DOWN, buff=1)
        self.add(everything)
        self.wait()
