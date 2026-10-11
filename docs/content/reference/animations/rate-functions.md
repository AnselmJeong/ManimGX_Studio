---
title: "Rate functions"
description: "How an animation paces itself: smoothly, steadily, with a rush, a bounce or a wiggle. Every rate function, to play and to scrub."
---

# Rate functions { #manimgx.animation.easing }

```python fold title="The film's code"
import manimgx as m


class RateFunctionsHero(m.Scene):
    def construct(self) -> None:
        rates = [m.smooth, m.linear, m.rush_into, m.there_and_back, m.ease_out_bounce]
        names = ["smooth", "linear", "rush_into", "there_and_back", "ease_out_bounce"]
        rows = m.VGroup()
        for name in names:
            label = m.Text(name, font="monospace", font_size=28)
            dot = m.Dot(radius=0.14, color=m.YELLOW)
            rows.add(m.VGroup(label, dot))
        rows.arrange(m.DOWN, buff=0.5)
        for row in rows:
            row[0].move_to([-2.2, row.get_y(), 0], aligned_edge=m.RIGHT)
            row[1].move_to([-1.4, row.get_y(), 0])
        self.add(rows)
        self.play(
            *[
                row[1].animate(rate_func=rate).shift(7 * m.RIGHT)
                for row, rate in zip(rows, rates, strict=True)
            ],
            run_time=3,
        )
        self.wait()
```

An animation runs from 0, its start, to 1, its end. Its rate function says how far along the
change is at each moment of that time: `rate_func(t)` for t from 0 to 1. The default,
[smooth][manimgx.smooth], starts slowly, speeds up and ends slowly; [linear][manimgx.linear]
keeps one speed. Give another to `play` or to any animation:
`self.play(square.animate.shift(m.RIGHT), rate_func=m.rush_into)`.

A rate function may go past 1 and back, for a bounce, or come back to 0, so that the
animation ends where it started. Choose one to see it move:

<div class="mx-rates" data-rates="smooth linear rush_into rush_from slow_into double_smooth there_and_back there_and_back_with_pause running_start lingering wiggle exponential_decay smoothstep smootherstep ease_in_back ease_in_bounce ease_in_circ ease_in_cubic ease_in_elastic ease_in_expo ease_in_out_back ease_in_out_bounce ease_in_out_circ ease_in_out_cubic ease_in_out_elastic ease_in_out_expo ease_in_out_quad ease_in_out_quart ease_in_out_quint ease_in_out_sine ease_in_quad ease_in_quart ease_in_quint ease_in_sine ease_out_back ease_out_bounce ease_out_circ ease_out_cubic ease_out_elastic ease_out_expo ease_out_quad ease_out_quart ease_out_quint ease_out_sine"></div>

## The usual ones

::: manimgx.smooth
    options:
      heading_level: 3

::: manimgx.linear
    options:
      heading_level: 3

::: manimgx.rush_into
    options:
      heading_level: 3

::: manimgx.rush_from
    options:
      heading_level: 3

::: manimgx.slow_into
    options:
      heading_level: 3

::: manimgx.double_smooth
    options:
      heading_level: 3

::: manimgx.there_and_back
    options:
      heading_level: 3

::: manimgx.there_and_back_with_pause
    options:
      heading_level: 3

::: manimgx.running_start
    options:
      heading_level: 3

::: manimgx.lingering
    options:
      heading_level: 3

::: manimgx.wiggle
    options:
      heading_level: 3

::: manimgx.exponential_decay
    options:
      heading_level: 3

::: manimgx.smoothstep
    options:
      heading_level: 3

::: manimgx.smootherstep
    options:
      heading_level: 3

## Easing curves

The easing curves are the web's: each eases in (starts slowly), eases out (ends slowly), or
both, with a curve of its own.

<div class="mx-rows" markdown>

::: manimgx.ease_in_back
    options:
      heading_level: 3

::: manimgx.ease_in_bounce
    options:
      heading_level: 3

::: manimgx.ease_in_circ
    options:
      heading_level: 3

::: manimgx.ease_in_cubic
    options:
      heading_level: 3

::: manimgx.ease_in_elastic
    options:
      heading_level: 3

::: manimgx.ease_in_expo
    options:
      heading_level: 3

::: manimgx.ease_in_out_back
    options:
      heading_level: 3

::: manimgx.ease_in_out_bounce
    options:
      heading_level: 3

::: manimgx.ease_in_out_circ
    options:
      heading_level: 3

::: manimgx.ease_in_out_cubic
    options:
      heading_level: 3

::: manimgx.ease_in_out_elastic
    options:
      heading_level: 3

::: manimgx.ease_in_out_expo
    options:
      heading_level: 3

::: manimgx.ease_in_out_quad
    options:
      heading_level: 3

::: manimgx.ease_in_out_quart
    options:
      heading_level: 3

::: manimgx.ease_in_out_quint
    options:
      heading_level: 3

::: manimgx.ease_in_out_sine
    options:
      heading_level: 3

::: manimgx.ease_in_quad
    options:
      heading_level: 3

::: manimgx.ease_in_quart
    options:
      heading_level: 3

::: manimgx.ease_in_quint
    options:
      heading_level: 3

::: manimgx.ease_in_sine
    options:
      heading_level: 3

::: manimgx.ease_out_back
    options:
      heading_level: 3

::: manimgx.ease_out_bounce
    options:
      heading_level: 3

::: manimgx.ease_out_circ
    options:
      heading_level: 3

::: manimgx.ease_out_cubic
    options:
      heading_level: 3

::: manimgx.ease_out_elastic
    options:
      heading_level: 3

::: manimgx.ease_out_expo
    options:
      heading_level: 3

::: manimgx.ease_out_quad
    options:
      heading_level: 3

::: manimgx.ease_out_quart
    options:
      heading_level: 3

::: manimgx.ease_out_quint
    options:
      heading_level: 3

::: manimgx.ease_out_sine
    options:
      heading_level: 3

</div>

## Make your own

A rate function is any Python function from a number to a number. These make one from
another.

::: manimgx.squish_rate_func
    options:
      heading_level: 3

::: manimgx.not_quite_there
    options:
      heading_level: 3

::: manimgx.unit_interval
    options:
      heading_level: 3

::: manimgx.zero
    options:
      heading_level: 3
