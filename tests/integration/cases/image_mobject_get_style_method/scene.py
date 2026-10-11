# Source: manim/mobject/types/image_mobject.py
import numpy as np

import manimgx as m


class ImageMobjectGetStyleMethod(m.Scene):
    def construct(self):
        img = m.ImageMobject(
            np.array(
                [[10, 20, 30, 255], [200, 100, 50, 255]],
                dtype=np.uint8,
            ).reshape(2, 1, 4)
        )
        style = img.get_style()
        # Use the returned fill_opacity to scale a marker placed beside the image.
        marker_height = float(style["fill_opacity"]) * 0.5
        marker = m.Square(side_length=marker_height).next_to(img, m.RIGHT)
        self.add(img, marker)
        self.wait(0.1)
