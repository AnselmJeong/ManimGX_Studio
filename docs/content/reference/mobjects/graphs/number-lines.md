---
title: "Number lines"
description: "One axis with ticks, numbers and labels, on an even or a logarithmic scale."
---

# Number lines

```python fold title="The film's code"
import manimgx as m


class NumberLinesHero(m.Scene):
    def construct(self) -> None:
        line = m.NumberLine(x_range=[-3, 3, 1], length=10, include_numbers=True)
        dot = m.Dot(line.n2p(-2), radius=0.12, color=m.YELLOW)
        interval = m.UnitInterval(length=8, include_numbers=True).shift(2 * m.DOWN)
        self.play(m.Create(line))
        self.play(m.GrowFromCenter(dot))
        self.play(dot.animate.move_to(line.n2p(2.5)), run_time=2)
        self.play(m.Create(interval))
        self.wait()
```

A number line is a line with a number at each of its points. Its range, `[start, end,
step]`, gives its first and last numbers and the step between its ticks; its length is in
the frame's units. [n2p][manimgx.NumberLine.number_to_point] turns a number into its point
on the line, to put anything at a number.

Axes are number lines too: each axis of [Axes][manimgx.Axes] is one, and takes the keywords
below.

::: manimgx.NumberLine
    options:
      heading_level: 2

::: manimgx.UnitInterval
    options:
      heading_level: 2

## Scales

A line's scale places its numbers: evenly, or by their logarithms. Give it as `scaling`.

::: manimgx.LinearBase
    options:
      heading_level: 3
      inherited_members: [function, inverse_function]

::: manimgx.LogBase
    options:
      heading_level: 3
      inherited_members: [function, inverse_function]
