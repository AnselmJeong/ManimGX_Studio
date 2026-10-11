---
title: "Scene"
description: "The scene: its construct method, the plays and waits that pass its time, the mobjects it shows, its sections, and the film it records."
---

# Scene

```python fold title="The film's code"
import manimgx as m


class SceneHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)
        self.add(square)
        self.wait(0.5)
        self.play(square.animate.shift(2 * m.RIGHT), run_time=1)
        self.next_section("turn")
        self.play(square.animate.rotate(m.PI / 4))
        self.remove(square)
        self.wait(0.5)
```

A scene runs its `construct` method once, from top to bottom, to make its video. Nothing in
`construct` shows until a play or an add puts it in the scene, and the scene's time moves
only in a play or a wait: each frame of the video shows the scene at its own exact time.

A scene also speaks and plays sounds: see [Sound](../sound/index.md) and
[Voice](../sound/voice.md).

::: manimgx.Scene
    options:
      heading_level: 2
      members: false

## What happens

::: manimgx.Scene.construct
    options:
      heading_level: 3

::: manimgx.Scene.setup
    options:
      heading_level: 3

::: manimgx.Scene.tear_down
    options:
      heading_level: 3

## Time

::: manimgx.Scene.play
    options:
      heading_level: 3

::: manimgx.Scene.wait
    options:
      heading_level: 3

::: manimgx.Scene.pause
    options:
      heading_level: 3

::: manimgx.Scene.wait_until
    options:
      heading_level: 3

::: manimgx.Scene.time
    options:
      heading_level: 3

## What it shows

::: manimgx.Scene.add
    options:
      heading_level: 3

::: manimgx.Scene.remove
    options:
      heading_level: 3

::: manimgx.Scene.clear
    options:
      heading_level: 3

::: manimgx.Scene.replace
    options:
      heading_level: 3

::: manimgx.Scene.bring_to_front
    options:
      heading_level: 3

::: manimgx.Scene.bring_to_back
    options:
      heading_level: 3

::: manimgx.Scene.add_foreground_mobjects
    options:
      heading_level: 3

::: manimgx.Scene.remove_foreground_mobjects
    options:
      heading_level: 3

::: manimgx.Scene.mobjects
    options:
      heading_level: 3

::: manimgx.Scene.foreground_mobjects
    options:
      heading_level: 3

## The scene's own updaters

::: manimgx.Scene.add_updater
    options:
      heading_level: 3

::: manimgx.Scene.remove_updater
    options:
      heading_level: 3

## Sections

::: manimgx.Scene.next_section
    options:
      heading_level: 3

## Its camera and its film

::: manimgx.Scene.camera
    options:
      heading_level: 3

::: manimgx.Scene.frame
    options:
      heading_level: 3

::: manimgx.Scene.three_d
    options:
      heading_level: 3

::: manimgx.Scene.film
    options:
      heading_level: 3

::: manimgx.Scene.num_plays
    options:
      heading_level: 3
