# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class GetGraphLabelExample(m.Scene):
    def construct(self):
        ax = m.Axes()
        sin = ax.plot(lambda x: np.sin(x), color=m.PURPLE_B)
        numerator = m.MathTex(r"\pi")
        denominator = m.MathTex("2")
        bar = m.Line(m.LEFT, m.RIGHT).scale_to_fit_width(
            max(numerator.width, denominator.width) * 1.25
        )
        label_tex = m.VGroup(numerator, bar, denominator).arrange(m.DOWN, buff=0.04)
        label = ax.get_graph_label(
            graph=sin,
            label=label_tex,
            x_val=m.PI / 2,
            dot=True,
            direction=m.UR,
        )

        self.add(ax, sin, label)
        self.wait()
