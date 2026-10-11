---
title: "Updaters"
description: "Rules a mobject keeps at every frame: follow another mobject, show a number, redraw itself, or move as time passes."
---

# Updaters

```python fold title="The film's code"
import manimgx as m


class UpdatersHero(m.Scene):
    def construct(self) -> None:
        dot = m.Dot(color=m.YELLOW).shift(3 * m.LEFT)
        label = m.Text("dot", font_size=36)
        label.add_updater(lambda mob: mob.next_to(dot, m.UP))
        trail = m.TracedPath(dot.get_center, stroke_color=m.YELLOW, stroke_width=4)
        self.add(trail, dot, label)
        self.play(dot.animate.shift(6 * m.RIGHT), run_time=2)
        self.play(m.Rotate(dot, m.PI, about_point=m.ORIGIN), run_time=2)
        self.wait()
```

An animation changes a mobject for its run time. An updater changes it at every frame, for
as long as it is attached: it keeps a rule while other things move. A label stays above a
dot, a number shows where a tracker is, a shape turns as time passes.

An updater is a function: ManimGX calls it with the mobject at every frame, in plays and in
waits alike. A function that also takes `dt` gets the time since it last ran, in seconds,
for motion that goes on: `lambda mob, dt: mob.rotate(dt)` turns a mobject a radian a
second.

## Add an updater

::: manimgx.Mobject.add_updater
    options:
      heading_level: 3

::: manimgx.Mobject.remove_updater
    options:
      heading_level: 3

::: manimgx.Mobject.clear_updaters
    options:
      heading_level: 3

::: manimgx.Mobject.get_updaters
    options:
      heading_level: 3

::: manimgx.Mobject.suspend_updating
    options:
      heading_level: 3

::: manimgx.Mobject.resume_updating
    options:
      heading_level: 3

::: manimgx.Mobject.update
    options:
      heading_level: 3

::: manimgx.Mobject.always
    options:
      heading_level: 3

## How time-based updaters run

ManimGX runs a time-based updater at each tick of the simulation clock, 60 times a second
whatever the frame rate, so that a simulation gives the same result at every frame rate. A
flow, which does the same however its time is split, runs at every frame instead; a recorder,
which reads the world, runs after everything else.

::: manimgx.mobject.flow
    options:
      heading_level: 3

::: manimgx.mobject.record
    options:
      heading_level: 3

## Ready-made updaters

::: manimgx.always_redraw
    options:
      heading_level: 3

::: manimgx.always_rotate
    options:
      heading_level: 3

::: manimgx.always_shift
    options:
      heading_level: 3

::: manimgx.turn_animation_into_updater
    options:
      heading_level: 3

::: manimgx.cycle_animation
    options:
      heading_level: 3

## Updaters as animations

::: manimgx.UpdateFromFunc
    options:
      heading_level: 3

::: manimgx.UpdateFromAlphaFunc
    options:
      heading_level: 3

::: manimgx.MaintainPositionRelativeTo
    options:
      heading_level: 3

## Trails and outlines

::: manimgx.TracedPath
    options:
      heading_level: 3

::: manimgx.AnimatedBoundary
    options:
      heading_level: 3
