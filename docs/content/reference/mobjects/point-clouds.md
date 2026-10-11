---
title: "Point clouds"
description: "Mobjects drawn as points, each a dot of its own color."
---

# Point clouds

```python fold title="The film's code"
import manimgx as m
import numpy as np


class PointCloudsHero(m.Scene):
    def construct(self) -> None:
        rng = np.random.default_rng(3)
        angles = rng.uniform(0, 2 * np.pi, 2000)
        radii = 3 * np.sqrt(rng.uniform(0, 1, 2000))
        points = np.stack(
            [radii * np.cos(angles), radii * np.sin(angles), np.zeros(2000)], axis=1
        )
        rgbas = np.array(
            [m.interpolate_color(m.BLUE, m.YELLOW, r / 3).to_rgba() for r in radii]
        )
        cloud = m.PMobject(stroke_width=6).add_points(points, rgbas)
        self.play(m.FadeIn(cloud))
        self.play(m.Rotate(cloud, m.PI / 2), run_time=2)
        self.wait()
```

A point cloud is a mobject drawn as points: each point a dot of its own color, as wide as
the cloud's stroke. Clouds suit what is many and small: dust, stars, samples.

::: manimgx.PMobject
    options:
      heading_level: 2

::: manimgx.PointCloudDot
    options:
      heading_level: 2
