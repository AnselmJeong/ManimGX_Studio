# Updaters

Sometimes a mobject must follow a rule while others move: a label stays above a dot, or a
number shows where a dot is. An updater is a function that keeps such a rule. ManimGX
calls it at every frame.

## Follow another mobject

```python
import manimgx as m


class Follow(m.Scene):
    def construct(self) -> None:
        dot = m.Dot(color=m.YELLOW)
        label = m.Text("dot", font_size=32)

        def stay_above(mobject: m.Mobject) -> None:
            mobject.next_to(dot, m.UP)

        label.add_updater(stay_above)
        self.add(dot, label)
        self.play(dot.animate.shift(4 * m.RIGHT))
        self.play(dot.animate.shift(3 * m.DOWN))
```

`label.add_updater(stay_above)` makes ManimGX call `stay_above(label)` at every frame. So
the label stays above the dot, wherever the dot goes. `label.clear_updaters()` stops it.

## A number that you animate

A [`ValueTracker`][manimgx.ValueTracker] holds a number. It doesn't show anything, but
you can animate its number, and updaters can read it. So one animation can move many
mobjects:

```python
import manimgx as m


class Counter(m.Scene):
    def construct(self) -> None:
        x = m.ValueTracker(0)
        number = m.DecimalNumber(0, font_size=96)

        def show_x(mobject: m.DecimalNumber) -> None:
            mobject.set_value(x.get_value())

        number.add_updater(show_x)
        self.add(number)
        self.play(x.animate.set_value(10), run_time=3)
```

`x.animate.set_value(10)` changes the number from 0 to 10, in 3 seconds.
`x.get_value()` reads it.

## Make a mobject again at every frame

`m.always_redraw` takes a function that makes a mobject, and makes it again at every
frame. Here, a dot rides a graph as a tracker moves:

```python
import manimgx as m


def curve(x: float) -> float:
    return x**2 / 4


class Ride(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[0, 5, 1], y_range=[0, 7, 1], x_length=8, y_length=5)
        graph = axes.plot(curve, color=m.BLUE)
        x = m.ValueTracker(1)

        def make_dot() -> m.Dot:
            point = axes.c2p(x.get_value(), curve(x.get_value()))
            return m.Dot(point, color=m.YELLOW)

        dot = m.always_redraw(make_dot)
        self.add(axes, graph, dot)
        self.play(x.animate.set_value(4.5), run_time=3)
```

## Motion that goes on

An updater can also take `dt`: the time, in seconds, since it last ran. Use it for motion
that goes on as time passes, in plays and in waits:

```python
import manimgx as m


class Spin(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)

        def turn(mobject: m.Mobject, dt: float) -> None:
            mobject.rotate(dt * m.PI)

        square.add_updater(turn)
        self.add(square)
        self.wait(2)
```

`dt * m.PI` turns the square half a turn each second. Updaters that take `dt` can also
simulate physics: the [Gallery](../gallery/index.md) has examples, such as
[a spinning top](../gallery/heavy-top.md).

## Next

[Camera and 3D](camera-and-3d.md) shows how to move the camera, and how to make scenes
in three dimensions.
