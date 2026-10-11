---
title: "Animations"
description: "What changes mobjects over time: how long a change takes, how it paces itself, and every kind of animation."
---

# Animations

```python fold title="The film's code"
import manimgx as m


class AnimationsHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)
        circle = m.Circle(color=m.PINK, fill_opacity=0.5)
        self.play(m.Create(square))
        self.play(square.animate.shift(2 * m.LEFT).rotate(m.PI / 4))
        self.play(m.Transform(square, circle))
        self.play(m.Indicate(square))
        self.play(square.animate.set_color(m.YELLOW).shift(2 * m.RIGHT))
        self.wait()
```

An animation changes mobjects over time. [play][manimgx.Scene.play] plays it: the scene's
time runs for the animation's `run_time` (1 second unless you give another), and every
frame shows the change at that moment. Its `rate_func` paces it: slowly, then fast, then
slowly, unless you give another.

Any change a method makes animates: put `.animate` before the method,
`self.play(square.animate.shift(m.RIGHT))`. The animations below make the changes a method
can't: draw a shape in, write a text, turn one mobject into another, flash a point. Several
play together in one `play`, or one after another in a group.

<div class="grid cards mx-cards" markdown>

-   ![](film:AnimateHero)

    [**Animate a change**](animate.md)

    ---

    `.animate`: any method call, animated. Move to a target, or back to a saved state.

-   ![](film:RateFunctionsHero)

    [**Rate functions**](rate-functions.md)

    ---

    How an animation paces itself: smoothly, steadily, with a bounce or a wiggle.

-   ![](film:AppearHero)

    [**Appear and disappear**](appear-and-disappear.md)

    ---

    Draw, write, fade and grow mobjects in, and take them out again.

-   ![](film:TransformsHero)

    [**Transforms**](transforms.md)

    ---

    Turn one mobject into another, match the parts of two formulas, swap places.

-   ![](film:MoveAndDeformHero)

    [**Move and deform**](move-and-deform.md)

    ---

    Turn about a point, follow a path, or carry every point through a function.

-   ![](film:EmphasisHero)

    [**Emphasis**](emphasis.md)

    ---

    Draw the eye: indicate, circumscribe, flash, wiggle.

-   ![](film:TogetherHero)

    [**Together and in turn**](together-and-in-turn.md)

    ---

    Play animations at once, one after another, or each shortly after the last.

</div>

## The animation

Every animation takes the animation keywords: how long it runs, how it paces itself, and how
its parts start one after another.

::: manimgx.animation.timeline.AnimationOptions
    options:
      heading_level: 3
      inherited_members: true
      members: [run_time, rate_func, lag_ratio, reverse_rate_function, remover, introducer, suspend_mobject_updating, use_override, name]

::: manimgx.Animation
    options:
      heading_level: 3
