# Source: manim/mobject/types/image_mobject.py
import numpy as np

import manimgx as m


class ImageMobjectSetColorAlphaKwarg(m.Scene):
    def construct(self):
        img = m.ImageMobject(
            np.array(
                [[127, 127, 127, 255], [127, 127, 127, 255]],
                dtype=np.uint8,
            ).reshape(2, 1, 4)
        )
        img.set_color("#ff8000", alpha=0.5)
        self.add(img)
        self.wait(0.1)
