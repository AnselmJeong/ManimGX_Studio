---
title: "Animate a change"
description: "Put `.animate` before a method, and play animates the change it makes; or move a mobject to a target, or back to a saved state."
---

# Animate a change

```python fold title="The film's code"
import manimgx as m


class AnimateHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)
        self.play(m.Create(square))
        self.play(square.animate.shift(3 * m.RIGHT).set_color(m.YELLOW))
        self.play(square.animate(run_time=2).rotate(m.PI / 2).scale(0.5))
        self.play(square.animate.move_to(m.ORIGIN).set_color(m.BLUE))
```

`square.shift(m.RIGHT)` moves the square at once. `square.animate.shift(m.RIGHT)` makes an
animation that moves it: give it to `play`, and the square moves for the animation's run
time. Chain several calls after `.animate`, and they happen together. Give `.animate` the
animation keywords, `square.animate(run_time=2)`, to time it.

`.animate` goes from the mobject as it is when the animation starts to the mobject as the
calls leave it: each point travels on a straight line, unless you give a `path_arc`.

::: manimgx.Mobject.animate
    options:
      heading_level: 2

::: manimgx.Animate
    options:
      heading_level: 2

## To a prepared state

::: manimgx.MoveToTarget
    options:
      heading_level: 3

::: manimgx.Restore
    options:
      heading_level: 3
