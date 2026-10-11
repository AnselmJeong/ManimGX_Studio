---
title: "Text and math"
description: "Words, formulas, numbers and code, set by Typst inside ManimGX, in fonts that come with it."
---

# Text and math

```python fold title="The film's code"
import manimgx as m


class TextAndMathHero(m.Scene):
    def construct(self) -> None:
        title = m.Text("The Pythagorean theorem", font_size=56)
        formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=80)
        formula[2].set_color(m.YELLOW)
        number = m.DecimalNumber(
            3.14159, num_decimal_places=4, font_size=56, color=m.BLUE
        )
        lines = m.VGroup(title, formula, number).arrange(m.DOWN, buff=0.7)
        self.play(m.Write(title))
        self.play(m.Write(formula))
        self.play(m.FadeIn(number))
        self.wait()
```

ManimGX sets text and formulas itself, with [Typst](https://typst.app) and the fonts that
come with it: you install no LaTeX and no fonts, and a text looks the same on every
computer. A text is a mobject made of its glyphs, so it moves, scales, colors and animates
as any shape does.

Write words with [Text][manimgx.Text], a formula in LaTeX with
[MathTex][manimgx.MathTex], words with formulas in them with [Tex][manimgx.Tex], and Typst
markup with [Typst][manimgx.Typst]. A number that changes is a
[DecimalNumber][manimgx.DecimalNumber].

<div class="grid cards mx-cards" markdown>

-   ![](film:TextHero)

    [**Text**](text.md)

    ---

    Words in a font, paragraphs, titles, bulleted lists and code.

-   ![](film:MathHero)

    [**Math**](math.md)

    ---

    Formulas in LaTeX or Typst, and their parts, to color, move and match.

-   ![](film:NumbersHero)

    [**Numbers**](numbers.md)

    ---

    Numbers written with a set number of decimal places, which can change as a scene plays.

</div>
