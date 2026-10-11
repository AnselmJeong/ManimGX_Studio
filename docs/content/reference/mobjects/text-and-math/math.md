---
title: "Math"
description: "Formulas in LaTeX or in Typst, typeset by ManimGX, and the parts of a formula to color, move and match."
---

# Math

```python fold title="The film's code"
import manimgx as m


class MathHero(m.Scene):
    def construct(self) -> None:
        before = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        after = m.MathTex("a^2", "=", "c^2", "-", "b^2", font_size=96)
        before[2].set_color(m.YELLOW)
        after[4].set_color(m.YELLOW)
        self.play(m.Write(before))
        self.play(m.TransformMatchingTex(before, after))
        self.wait()
```

[MathTex][manimgx.MathTex] typesets a formula written in LaTeX: fractions, roots, sums and
integrals, matrices, `cases`, Greek letters. Write it in a raw string, `r"..."`, so that
Python keeps its backslashes. LaTeX packages and `\def` don't work; a command ManimGX
doesn't know stops the scene with its name.

Give `MathTex` several strings, and each one is a part of the formula, to color, move or
animate alone: `MathTex("a^2", "+", "b^2")[2]` is the b². Parts that are written the same
in two formulas move into each other with
[TransformMatchingTex][manimgx.TransformMatchingTex].

[Tex][manimgx.Tex] is text with formulas in it, between `$` signs. If you know Typst, write
it directly: [Typst][manimgx.Typst] takes Typst markup, and
[MathTypst][manimgx.MathTypst] a formula in Typst's math syntax.

::: manimgx.MathTex
    options:
      heading_level: 2

::: manimgx.MathTexPart
    options:
      heading_level: 2

::: manimgx.Tex
    options:
      heading_level: 2

::: manimgx.Typst
    options:
      heading_level: 2

::: manimgx.MathTypst
    options:
      heading_level: 2

## A typeset text's parts

Every text and formula is made of glyphs, as Typst sets them: each knows which characters of
its source it draws. A source Typst can't set stops the scene with Typst's error.

::: manimgx.mobjects.text.TypstGlyph
    options:
      heading_level: 3

::: manimgx.drawing.typesetting.TypstError
    options:
      heading_level: 3
