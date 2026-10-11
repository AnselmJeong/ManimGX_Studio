# Source: docs/source/examples.rst
import numpy as np

import manimgx as m


class GradientImageFromArray(m.Scene):
    def construct(self):
        n = 256
        imageArray = np.array(
            [[i * 256 / n for i in range(n)] for _ in range(n)], dtype=np.uint8
        )
        image = m.ImageMobject(imageArray).scale(2)
        image.background_rectangle = m.SurroundingRectangle(image, color=m.GREEN)
        self.add(image, image.background_rectangle)
