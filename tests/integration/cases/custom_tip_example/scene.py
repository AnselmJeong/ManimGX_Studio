# Source: manim/mobject/geometry/tips.py
import numpy as np

import manimgx as m


class MyCustomArrowTip(m.ArrowTip, m.RegularPolygon):
    def __init__(
        self,
        length: float = 0.35,
        width: float | None = None,
        color: str = "white",
        **kwargs: object,
    ) -> None:
        del width, kwargs
        m.RegularPolygon.__init__(
            self, n=5, color=color, fill_opacity=1.0, stroke_width=0.0
        )
        self.width = length
        self.stretch_to_fit_height(length)


arr = m.Arrow(np.array([-2, -2, 0]), np.array([2, 2, 0]), tip_shape=MyCustomArrowTip)


class CustomTipExample(m.Scene):
    def construct(self):
        self.play(m.Create(arr))
