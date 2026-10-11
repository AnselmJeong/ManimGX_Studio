---
title: "Copies and states"
description: "Copy a mobject, keep its state to return to, prepare a state to move to, or make it look like another."
---

# Copies and states

```python fold title="The film's code"
import manimgx as m


class CopiesAndStatesHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.6)
        self.play(m.Create(square))
        square.save_state()
        copy = square.copy().set_color(m.YELLOW)
        self.play(copy.animate.shift(3 * m.RIGHT))
        target = square.generate_target()
        target.shift(3 * m.LEFT).rotate(m.PI / 4).set_color(m.RED)
        self.play(m.MoveToTarget(square))
        self.play(m.Restore(square))
        self.wait()
```

A mobject is one object in the scene: a variable that names it names that object, and a
change to it shows wherever it is. To have two, copy it. To change a mobject and come
back, keep its state first. To animate a change into a state that you prepare step by step,
make its target.

::: manimgx.Mobject.copy
    options:
      heading_level: 2

## Keep a state

::: manimgx.Mobject.save_state
    options:
      heading_level: 3

::: manimgx.Mobject.restore
    options:
      heading_level: 3

## Prepare a state

::: manimgx.Mobject.generate_target
    options:
      heading_level: 3

::: manimgx.Mobject.target
    options:
      heading_level: 3

## Look like another

::: manimgx.Mobject.become
    options:
      heading_level: 3

::: manimgx.Mobject.match_points
    options:
      heading_level: 3
