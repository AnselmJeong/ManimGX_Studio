---
title: "Value trackers"
description: "A number you animate: it shows nothing, and updaters read it, so one animation can move many mobjects."
---

# Value trackers

```python fold title="The film's code"
import manimgx as m


def curve(x: float) -> float:
    return x**2 / 4


class ValueTrackersHero(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[0, 5, 1], y_range=[0, 7, 1], x_length=8, y_length=5)
        graph = axes.plot(curve, color=m.BLUE)
        x = m.ValueTracker(1)
        dot = m.always_redraw(
            lambda: m.Dot(axes.c2p(x.get_value(), curve(x.get_value())), color=m.YELLOW)
        )
        number = m.always_redraw(
            lambda: m.DecimalNumber(x.get_value()).next_to(dot, m.UL)
        )
        self.add(axes, graph, dot, number)
        self.play(x.animate.set_value(4.5), run_time=3)
        self.wait()
```

A value tracker holds a number and shows nothing. Animate its number with
`tracker.animate.set_value(10)`; read it with `tracker.get_value()` in an updater, or in a
function that [always_redraw][manimgx.always_redraw] calls. One animation of a tracker then
moves every mobject that reads it.

::: manimgx.ValueTracker
    options:
      heading_level: 2

::: manimgx.ComplexValueTracker
    options:
      heading_level: 2
