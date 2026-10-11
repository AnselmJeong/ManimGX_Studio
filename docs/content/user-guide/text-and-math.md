# Text and math

ManimGX sets text and formulas itself, with [Typst](https://typst.app) and fonts that come
with it. You don't install LaTeX or fonts, and your text looks the same on every computer.

## Text

`m.Text` shows text exactly as you write it. A new line (`\n`) starts a new line:

```python
import manimgx as m


class Words(m.Scene):
    def construct(self) -> None:
        title = m.Text("The Pythagorean theorem", font_size=64)
        note = m.Text("for a right triangle", font_size=36, color=m.GREY_B)
        note.next_to(title, m.DOWN)
        self.play(m.Write(title))
        self.play(m.FadeIn(note))
```

- `font_size` sets the size: 48 unless you give another.
- `font` sets the font: `"sans-serif"`, `"monospace"`, or the name of a font on your
  computer. The default is New Computer Modern, the font of LaTeX.
- `t2c` colors parts of the text: `m.Text("red and blue", t2c={"red": m.RED, "blue": m.BLUE})`.

Text is a mobject like any other: you can move it, scale it, color it and animate it.

## Formulas

`m.MathTex` shows a formula, written in LaTeX math. Write it in a raw string, `r"..."`,
so that Python keeps its backslashes:

```python
import manimgx as m


class Formula(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex(r"\int_0^1 x^2 \, dx = \frac{1}{3}", font_size=72)
        self.play(m.Write(formula))
```

Fractions, roots, sums and integrals, matrices, `cases`, Greek letters, `\mathbb` and
`\text` work. LaTeX packages and `\def` don't. If ManimGX doesn't know a command, its
error names the command.

`m.Tex` is for text with math in it: `m.Tex(r"The area is $\pi r^2$.")`.

## Parts of a formula

Give `m.MathTex` several strings, and each one becomes a part that you can color or
animate on its own. `formula[2]` is the third part:

```python
import manimgx as m


class Parts(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        formula[2].set_color(m.YELLOW)
        self.play(m.Write(formula))
        self.play(m.Indicate(formula[2]))
```

## Change a formula into another

`m.TransformMatchingTex` moves each part of a formula to the part with the same LaTeX
in another formula. The parts that don't match fade out and in:

```python
import manimgx as m


class Rearrange(m.Scene):
    def construct(self) -> None:
        before = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        after = m.MathTex("a^2", "=", "c^2", "-", "b^2", font_size=96)
        before[2].set_color(m.YELLOW)
        after[4].set_color(m.YELLOW)
        self.play(m.Write(before))
        self.play(m.TransformMatchingTex(before, after))
        self.wait()
```

## Numbers

`m.DecimalNumber(3.14)` shows a number. Its `set_value` shows a different one in its
place, so a number can count up or down as a scene plays: [Updaters](updaters.md) shows
how.

## Typst

If you know [Typst](https://typst.app), write in it directly: `m.Typst` takes Typst
markup, and `m.MathTypst` a formula in Typst's math syntax.

```py
m.Typst("*Bold*, _italic_, and math: $sum_(k=1)^n k = (n(n+1))/2$")
```

## Next

[Graphs](graphs.md) shows how to draw axes and plot functions, with labels.
