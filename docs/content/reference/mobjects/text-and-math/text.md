---
title: "Text"
description: "Words in a font, paragraphs, titles, bulleted lists and code listings."
---

# Text

```python fold title="The film's code"
import manimgx as m


class TextHero(m.Scene):
    def construct(self) -> None:
        title = m.Text("Text", font_size=72)
        styles = m.VGroup(
            m.Text("bold", weight=m.BOLD, font_size=40),
            m.Text("italic", slant=m.ITALIC, font_size=40),
            m.Text("monospace", font="monospace", font_size=40),
            m.Text("red and blue", t2c={"red": m.RED, "blue": m.BLUE}, font_size=40),
        ).arrange(buff=0.6)
        items = m.BulletedList("one idea", "at a time", font_size=40)
        page = m.VGroup(title, styles, items).arrange(m.DOWN, buff=0.7)
        self.play(m.Write(title))
        self.play(m.LaggedStart(*[m.FadeIn(style) for style in styles], lag_ratio=0.2))
        self.play(m.Write(items))
        self.wait()
```

[Text][manimgx.Text] writes words exactly as you give them, in a font: a new line (`\n`)
starts a new line. Its size is `font_size`, 48 unless you give another. Its parts are its
characters, so `text[0]` is the first one; `t2c` colors parts of it by their words.

A title, a bulleted list and a paragraph arrange lines of text for you, and a code listing
highlights a program's source.

::: manimgx.Text
    options:
      heading_level: 2

::: manimgx.Paragraph
    options:
      heading_level: 2

::: manimgx.Title
    options:
      heading_level: 2

::: manimgx.BulletedList
    options:
      heading_level: 2

::: manimgx.Code
    options:
      heading_level: 2

::: manimgx.mobjects.code.CodeText
    options:
      heading_level: 3

## Weights and slants

A text's `weight` is how heavy its strokes are, and its `slant` how it leans.

<div class="mx-constants" markdown>

::: manimgx.NORMAL
    options:
      heading_level: 3

::: manimgx.ITALIC
    options:
      heading_level: 3

::: manimgx.OBLIQUE
    options:
      heading_level: 3

::: manimgx.THIN
    options:
      heading_level: 3

::: manimgx.ULTRALIGHT
    options:
      heading_level: 3

::: manimgx.LIGHT
    options:
      heading_level: 3

::: manimgx.SEMILIGHT
    options:
      heading_level: 3

::: manimgx.BOOK
    options:
      heading_level: 3

::: manimgx.MEDIUM
    options:
      heading_level: 3

::: manimgx.SEMIBOLD
    options:
      heading_level: 3

::: manimgx.BOLD
    options:
      heading_level: 3

::: manimgx.ULTRABOLD
    options:
      heading_level: 3

::: manimgx.HEAVY
    options:
      heading_level: 3

::: manimgx.ULTRAHEAVY
    options:
      heading_level: 3

</div>
