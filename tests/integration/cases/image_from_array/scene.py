# Source: manim/mobject/types/image_mobject.py
import numpy as np

import manimgx as m


class ImageFromArray(m.Scene):
    def construct(self):
        image = m.ImageMobject(
            np.array([[0, 100, 30, 200], [255, 0, 5, 33]], dtype=np.uint8)
        )
        image.height = 7
        self.add(image)
