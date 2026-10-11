---
title: "Images and SVG"
description: "Pictures from image files or arrays of pixels, and drawings read from SVG files, whose shapes are paths."
---

# Images and SVG

```python fold title="The film's code"
import manimgx as m
import numpy as np


class ImagesAndSvgHero(m.Scene):
    def construct(self) -> None:
        x = np.linspace(-1, 1, 64)
        pixels = np.zeros((64, 64, 3), dtype=np.uint8)
        pixels[..., 0] = 255 * (x[None, :] + 1) / 2
        pixels[..., 2] = 255 * (x[:, None] + 1) / 2
        image = m.ImageMobject(pixels).scale_to_fit_height(4)
        image.set_resampling_algorithm(m.RESAMPLING_ALGORITHMS["nearest"])
        self.play(m.FadeIn(image))
        self.play(image.animate.rotate(m.PI / 8).scale(0.8))
        self.wait()
```

An image is a picture on a rectangle: read from a file (PNG, JPEG and the rest), or made from
an array of pixels. It moves, scales, turns and fades as any mobject; its pixels stay its
own. An SVG drawing is different: its shapes become paths, each a part to color, move and
draw in, as a shape of ManimGX's own.

::: manimgx.ImageMobject
    options:
      heading_level: 2

::: manimgx.RESAMPLING_ALGORITHMS
    options:
      heading_level: 3

::: manimgx.constants.Resampling
    options:
      heading_level: 3

::: manimgx.SVGMobject
    options:
      heading_level: 2

::: manimgx.mobjects.svg.PathOptions
    options:
      heading_level: 3
