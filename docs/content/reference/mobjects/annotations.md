---
title: "Annotations"
description: "What points at, frames, labels and measures other mobjects: braces, labels, frames, underlines, crosses and angle marks."
---

# Annotations

```python fold title="The film's code"
import manimgx as m


class AnnotationsHero(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex(r"a^2 + b^2 = c^2", font_size=72).shift(1.5 * m.UP)
        brace = m.Brace(formula[0][:5], m.DOWN, color=m.YELLOW)
        note = brace.get_text("the legs")
        frame = m.SurroundingRectangle(formula[0][6:], color=m.BLUE)
        a, b, c = [-1.5, -3, 0], [1.5, -3, 0], [1.5, -0.8, 0]
        triangle = m.Polygon(a, b, c, color=m.WHITE)
        right = m.RightAngle(m.Line(b, a), m.Line(b, c), length=0.35, color=m.GREEN)
        angle = m.Angle(m.Line(a, b), m.Line(a, c), radius=0.8, color=m.RED)
        self.play(m.Write(formula))
        self.play(m.GrowFromCenter(brace), m.FadeIn(note), m.Create(frame))
        self.play(m.Create(triangle), m.Create(right), m.Create(angle))
        self.wait()
```

An annotation points at another mobject, frames it, labels it or measures it. Most take the
mobject when you make them and fit it: a brace as long as its side, a frame around it, a
line under it. They don't follow it afterward; to make one follow, redraw it at every frame
with [always_redraw][manimgx.always_redraw].

## Braces

::: manimgx.Brace
    options:
      heading_level: 3

::: manimgx.BraceBetweenPoints
    options:
      heading_level: 3

::: manimgx.ArcBrace
    options:
      heading_level: 3

::: manimgx.BraceLabel
    options:
      heading_level: 3

::: manimgx.BraceText
    options:
      heading_level: 3

## Frames and marks

::: manimgx.SurroundingRectangle
    options:
      heading_level: 3

::: manimgx.BackgroundRectangle
    options:
      heading_level: 3

::: manimgx.mobjects.annotations.FrameOptions
    options:
      heading_level: 3

::: manimgx.Underline
    options:
      heading_level: 3

::: manimgx.Cross
    options:
      heading_level: 3

::: manimgx.AnnotationDot
    options:
      heading_level: 3

## Labels

::: manimgx.Label
    options:
      heading_level: 3

::: manimgx.LabeledDot
    options:
      heading_level: 3

::: manimgx.LabeledLine
    options:
      heading_level: 3

::: manimgx.LabeledArrow
    options:
      heading_level: 3

::: manimgx.LabeledPolygram
    options:
      heading_level: 3

## Angles

::: manimgx.Angle
    options:
      heading_level: 3

::: manimgx.RightAngle
    options:
      heading_level: 3

::: manimgx.Elbow
    options:
      heading_level: 3
