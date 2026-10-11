---
title: "Emphasis"
description: "Draw the eye to a mobject: indicate it, circle it, flash a point, wiggle it, blink it."
---

# Emphasis

```python fold title="The film's code"
import manimgx as m


class EmphasisHero(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        self.add(formula)
        self.play(m.Indicate(formula[0]))
        self.play(m.Circumscribe(formula[2], color=m.YELLOW))
        self.play(m.Flash(formula[4], color=m.YELLOW, flash_radius=0.8))
        self.play(m.Wiggle(formula))
        self.wait()
```

These animations change a mobject for a moment and give it back as it was: they point a
viewer's eye at it while the voice talks about it.

::: manimgx.Indicate
    options:
      heading_level: 2

::: manimgx.Circumscribe
    options:
      heading_level: 2

::: manimgx.Flash
    options:
      heading_level: 2

::: manimgx.FocusOn
    options:
      heading_level: 2

::: manimgx.Wiggle
    options:
      heading_level: 2

::: manimgx.ShowPassingFlash
    options:
      heading_level: 2

::: manimgx.ShowPassingFlashWithThinningStrokeWidth
    options:
      heading_level: 2

::: manimgx.Blink
    options:
      heading_level: 2

::: manimgx.Broadcast
    options:
      heading_level: 2
