# Source: manim/mobject/types/image_mobject.py
import numpy as np

import manimgx as m


class ImageMobjectSetOpacityAlphaKwarg(m.Scene):
    def construct(self):
        img = m.ImageMobject(
            np.array(
                [[200, 100, 50, 255], [100, 200, 50, 255]],
                dtype=np.uint8,
            ).reshape(2, 1, 4)
        )
        img.set_opacity(alpha=0.4)
        self.add(img)
        self.wait(0.1)
