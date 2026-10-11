---
title: "Numbers"
description: "Numbers written with a set number of decimal places, integers, and named values that follow a tracker."
---

# Numbers

```python fold title="The film's code"
import manimgx as m


class NumbersHero(m.Scene):
    def construct(self) -> None:
        number = m.DecimalNumber(0, num_decimal_places=2, font_size=96, color=m.YELLOW)
        variable = m.Variable(0, m.MathTex("x"), num_decimal_places=2).scale(1.5)
        tracker = variable.tracker
        m.VGroup(number, variable).arrange(m.DOWN, buff=1)

        def follow(mobject: m.DecimalNumber) -> None:
            mobject.set_value(tracker.get_value())

        number.add_updater(follow)
        self.add(number, variable)
        self.play(tracker.animate.set_value(3.14), run_time=2)
        self.wait()
```

A number is a text that knows its value. [set_value][manimgx.DecimalNumber.set_value] shows
another value in its place, with the same look, so a number can count while a scene plays:
by an [updater](../../updaters/index.md) that sets it at every frame, or by
[ChangeDecimalToValue][manimgx.ChangeDecimalToValue].

::: manimgx.DecimalNumber
    options:
      heading_level: 2

::: manimgx.Integer
    options:
      heading_level: 2

::: manimgx.Variable
    options:
      heading_level: 2

## Count to a value

::: manimgx.ChangeDecimalToValue
    options:
      heading_level: 3

::: manimgx.ChangingDecimal
    options:
      heading_level: 3
