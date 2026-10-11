---
title: "Ready-made scenes"
description: "Scenes made for one kind of video: vectors on a plane, linear transformations of the plane, and a zoomed inset."
---

# Ready-made scenes

```python fold title="The film's code"
import manimgx as m


class ReadyMadeScenesHero(m.LinearTransformationScene):
    def construct(self) -> None:
        self.add_vector([1, 2], color=m.YELLOW)
        self.apply_matrix([[1, 1], [0, 1]])
        self.wait()
```

These scenes come with what one kind of video needs. A vector scene draws vectors from the
origin of a plane, with their labels and their coordinates. A linear transformation scene
applies a matrix to the plane and to everything on it, in one play. A zoomed scene shows a
magnified part of the frame, in an inset.

::: manimgx.VectorScene
    options:
      heading_level: 2

::: manimgx.LinearTransformationScene
    options:
      heading_level: 2

::: manimgx.ZoomedScene
    options:
      heading_level: 2

::: manimgx.scene.ZoomedCameraConfig
    options:
      heading_level: 3
