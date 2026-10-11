# Source: manim/mobject/types/image_mobject.py
import numpy as np

import manimgx as m


class ImageInterpolationEx(m.Scene):
    def construct(self):
        img = m.ImageMobject(
            np.array(
                [[63, 0, 0, 0], [0, 127, 0, 0], [0, 0, 191, 0], [0, 0, 0, 255]],
                dtype=np.uint8,
            )
        )

        img.height = 3

        group = m.Group()
        algorithm_texts = ["nearest", "linear", "cubic"]
        for algorithm_text in algorithm_texts:
            algorithm = m.RESAMPLING_ALGORITHMS[algorithm_text]
            img_copy = img.copy().set_resampling_algorithm(algorithm)
            img_copy.add(m.Text(algorithm_text).scale(0.5).next_to(img_copy, m.UP))
            group.add(img_copy)

        group.arrange()
        self.add(group)
