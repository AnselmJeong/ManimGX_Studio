# Animations

An animation changes mobjects over time. [The basics](the-basics.md) showed the ones that
show and hide mobjects. This page shows how to animate any change, how to time an
animation, and how to play several together.

## Animate any change

Put `.animate` before a method, and `self.play` animates the change that the method makes:

```python
import manimgx as m


class Changes(m.Scene):
    def construct(self) -> None:
        square = m.Square()
        self.play(m.Create(square))
        self.play(square.animate.shift(3 * m.RIGHT))
        self.play(square.animate.rotate(45 * m.DEGREES))
        self.play(square.animate.set_fill(m.BLUE, opacity=1))
        self.play(square.animate.scale(0.5).move_to(m.ORIGIN))
```

Without `.animate`, `square.shift(3 * m.RIGHT)` moves the square at once, with no
animation. With `.animate`, the square moves there in one second. You can chain several
changes after `.animate`, as the last line does, and they occur together.

## Turn one mobject into another

`m.ReplacementTransform` turns one mobject into another:

```python
import manimgx as m


class SquareIntoCircle(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)
        circle = m.Circle(color=m.PINK, fill_opacity=0.5)
        self.play(m.Create(square))
        self.play(m.ReplacementTransform(square, circle))
        self.play(circle.animate.shift(2 * m.UP))
```

After it, `circle` is in the video, and `square` is not. `m.Transform(square, circle)`
looks the same, but it changes `square` into the shape of the circle and keeps it in
the video: after it, you move `square`, not `circle`.

## Time an animation

Most animations take one second. To choose how long, give a `run_time`, in seconds:

```py
self.play(m.Create(circle), run_time=3)
```

Its `rate_func` sets how fast it goes at each moment. The default, `m.smooth`, starts
slowly, speeds up, and ends slowly. `m.linear` keeps one speed. Choose one below to see
how it moves:

<div class="mx-rates" data-rates="smooth linear rush_into rush_from there_and_back double_smooth running_start lingering ease_in_out_sine ease_in_back ease_out_elastic ease_out_bounce"></div>

```py
self.play(square.animate.shift(3 * m.RIGHT), rate_func=m.linear)
```

The [rate functions][manimgx.animation.easing] reference lists all of them.

## Play animations together

Give `self.play` several animations, and they play at the same time. The play lasts as
long as the longest one:

```python
import manimgx as m


class Together(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        words = m.Text("A circle")
        words.next_to(circle, m.DOWN)
        self.play(m.Create(circle), m.Write(words))
        self.play(circle.animate.set_fill(m.RED, opacity=1), m.FadeOut(words))
```

## Play animations in turn

`m.LaggedStart` starts each animation a short time after the one before it. Its
`lag_ratio` sets when: 0.5 starts each one when the one before it is half done.

```python
import manimgx as m


class InTurn(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        square = m.Square()
        triangle = m.Triangle()
        shapes = m.VGroup(circle, square, triangle)
        shapes.arrange(m.RIGHT, buff=1)
        self.play(
            m.LaggedStart(
                m.Create(circle), m.Create(square), m.Create(triangle), lag_ratio=0.5
            )
        )
```

`m.Succession` plays its animations one after the other, in one play. Use it when the
steps are a part of a larger play: for example, to move a shape in three steps while a
title is written.

The [reference](../reference/animations/index.md) shows every animation.

## Next

[Text and math](text-and-math.md) shows how to write words and formulas, and how to
animate them.
