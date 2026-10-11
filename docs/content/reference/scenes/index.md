---
title: "Scenes"
description: "A scene is one video: its construct method says what happens, in order, and its time passes only in plays and waits."
---

# Scenes

```python fold title="The film's code"
import manimgx as m


class ScenesHero(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(color=m.BLUE, fill_opacity=0.5)
        words = m.Text("Hello!", font_size=72)
        self.play(m.Create(circle))
        self.play(m.FadeOut(circle))
        self.play(m.Write(words))
        self.wait()
```

A scene is one video. Make a class from [Scene][manimgx.Scene], and write what happens in its
`construct` method: ManimGX runs it from top to bottom, and each line adds to the video in
that order. The class's name is the video's: the scene `Hello` makes `Hello.mp4`.

Time passes only in [play][manimgx.Scene.play] and [wait][manimgx.Scene.wait]. A play starts
when the one before it ends and lasts as long as its longest animation; a wait holds the
picture, while updaters keep running. [add][manimgx.Scene.add] shows a mobject at once,
taking no time.

<div class="grid cards mx-cards" markdown>

-   ![](film:ScenesHero)

    [**Scene**](scene.md)

    ---

    What happens and when: plays and waits, what the scene shows, its sections and its film.

-   ![](film:ThreeDScenesHero)

    [**3D scenes**](../camera-and-3d/three-d-scenes.md)

    ---

    A scene seen in three dimensions, from a camera that turns around it.

-   ![](film:ReadyMadeScenesHero)

    [**Ready-made scenes**](ready-made-scenes.md)

    ---

    Scenes made for vectors, for linear transformations of the plane, and for a zoomed inset.

</div>
