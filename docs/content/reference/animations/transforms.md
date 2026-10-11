---
title: "Transforms"
description: "Turn one mobject into another: its shape and its style, part by part or by matching parts, along a straight path or an arc."
---

# Transforms

```python fold title="The film's code"
import manimgx as m


class TransformsHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5).shift(3 * m.LEFT)
        circle = m.Circle(color=m.PINK, fill_opacity=0.5).shift(3 * m.LEFT)
        star = m.Star(color=m.YELLOW, fill_opacity=0.5).shift(3 * m.RIGHT)
        self.play(m.Create(square))
        self.play(m.ReplacementTransform(square, circle))
        self.play(m.TransformFromCopy(circle, star, path_arc=m.PI / 2))
        self.play(m.Swap(circle, star))
        self.wait()
```

A transform turns one mobject into another: its points travel to the other's, and its style
blends into the other's. [ReplacementTransform][manimgx.ReplacementTransform] then puts the
other mobject in its place, so that you go on with the new one;
[Transform][manimgx.Transform] keeps the first mobject, now in the other's shape. To turn a
formula into another, part by part, match their parts:
[TransformMatchingTex][manimgx.TransformMatchingTex].

Each point travels on a straight line unless you give an arc: `path_arc=m.PI` sends each
point around half a circle. A path function chooses any other way.

::: manimgx.Transform
    options:
      heading_level: 2

::: manimgx.ReplacementTransform
    options:
      heading_level: 2

::: manimgx.TransformFromCopy
    options:
      heading_level: 2

::: manimgx.ClockwiseTransform
    options:
      heading_level: 2

::: manimgx.CounterclockwiseTransform
    options:
      heading_level: 2

::: manimgx.FadeTransform
    options:
      heading_level: 2

::: manimgx.FadeTransformPieces
    options:
      heading_level: 2

## Match the parts

::: manimgx.TransformMatchingTex
    options:
      heading_level: 3

::: manimgx.TransformMatchingShapes
    options:
      heading_level: 3

## Trade places

::: manimgx.Swap
    options:
      heading_level: 3

::: manimgx.CyclicReplace
    options:
      heading_level: 3

## The transform keywords

::: manimgx.animation.transform.TransformOptions
    options:
      heading_level: 3

## Paths

A path function says how each point travels from where it starts to where it ends: give one
as `path_func`.

::: manimgx.straight_path
    options:
      heading_level: 3

::: manimgx.path_along_arc
    options:
      heading_level: 3

::: manimgx.clockwise_path
    options:
      heading_level: 3

::: manimgx.counterclockwise_path
    options:
      heading_level: 3

::: manimgx.spiral_path
    options:
      heading_level: 3

::: manimgx.path_along_circles
    options:
      heading_level: 3

::: manimgx.Path
    options:
      heading_level: 3

::: manimgx.STRAIGHT_PATH_THRESHOLD
    options:
      heading_level: 3
