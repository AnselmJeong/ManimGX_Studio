---
title: "Together and in turn"
description: "Play animations at once, one after another, or each shortly after the one before it; slow down or speed up a play."
---

# Together and in turn

```python fold title="The film's code"
import manimgx as m


class TogetherHero(m.Scene):
    def construct(self) -> None:
        dots = m.VGroup(*[m.Dot(radius=0.2, color=m.YELLOW) for _ in range(6)]).arrange(
            buff=0.8
        )
        self.play(
            m.LaggedStart(*[m.GrowFromCenter(dot) for dot in dots], lag_ratio=0.3)
        )
        self.play(m.Succession(*[dot.animate.shift(m.UP) for dot in dots], run_time=2))
        self.play(m.AnimationGroup(*[dot.animate.shift(m.DOWN) for dot in dots]))
        self.wait()
```

`self.play(a, b)` plays a and b together. A group plays animations as one: together, one
after another, or each a little after the one before it. A group is an animation itself, so
groups nest, and a group plays inside a larger play.

::: manimgx.AnimationGroup
    options:
      heading_level: 2

::: manimgx.Succession
    options:
      heading_level: 2

::: manimgx.LaggedStart
    options:
      heading_level: 2

::: manimgx.LaggedStartMap
    options:
      heading_level: 2

::: manimgx.ChangeSpeed
    options:
      heading_level: 2

::: manimgx.Wait
    options:
      heading_level: 2

::: manimgx.Add
    options:
      heading_level: 2
