---
title: "Mobjects"
description: "What a video shows. Every mobject has a place in the frame, a size, a style and parts."
---

# Mobjects

```python fold title="The film's code"
import manimgx as m


class MobjectsHero(m.Scene):
    def construct(self) -> None:
        def curve(x: float) -> float:
            return 0.5 * x**2

        axes = m.Axes(x_range=[-2, 2, 1], y_range=[0, 2, 1], x_length=3.2, y_length=2.2)
        graph = axes.plot(curve, color=m.BLUE)
        kinds = m.VGroup(
            m.Square(color=m.BLUE, fill_opacity=0.5),
            m.Star(color=m.YELLOW, fill_opacity=0.5),
            m.Arrow(m.LEFT, m.RIGHT, color=m.GREEN),
            m.Text("Text", font_size=64),
            m.MathTex(r"e^{i\pi} + 1 = 0", font_size=56),
            m.VGroup(axes, graph),
        )
        kinds.arrange_in_grid(rows=2, buff=(1.2, 1))
        self.play(
            m.LaggedStart(
                *[m.FadeIn(kind, shift=0.3 * m.UP) for kind in kinds], lag_ratio=0.15
            )
        )
        self.wait()
```

A mobject is anything a video shows: a shape, a text, a formula, a graph. Making a mobject
doesn't show it: [add][manimgx.Scene.add] it to the scene, or [play][manimgx.Scene.play] an
animation that brings it in.

Every mobject has three things:

- **Points**, which give its place and its shape. They are in units: the frame's short side
  is 8 units, and its center is the point `[0, 0, 0]`.
- **A style**: the color and opacity of its stroke and of its fill.
- **Parts**, which are mobjects too: a group's members, a formula's terms, a graph's axes.
  What you do to a mobject, you do to all its parts.

Every mobject can do what the first pages tell, whatever its kind: be placed, sized and
turned, styled, grouped and copied. The pages after them tell each kind of mobject.

## What every mobject can do

<div class="grid cards mx-cards" markdown>

-   ![](film:PositionsHero)

    [**Positions**](positions.md)

    ---

    Points and directions, and the methods that place a mobject: at a point, by another
    mobject, at the frame's edge.

-   ![](film:SizeAndAngleHero)

    [**Size and angle**](size-and-angle.md)

    ---

    Scale, stretch, turn and flip a mobject, or move every point through a function.

-   ![](film:StyleHero)

    [**Style**](style.md)

    ---

    Stroke and fill, color and opacity, gradients, and what covers what.

-   ![](film:ColorsHero)

    [**Colors**](colors.md)

    ---

    The named colors, and the functions that make, blend and choose colors.

-   ![](film:GroupsHero)

    [**Groups**](groups.md)

    ---

    Mobjects made of mobjects: add, remove, arrange and sort the parts.

-   ![](film:CopiesAndStatesHero)

    [**Copies and states**](copies-and-states.md)

    ---

    Copy a mobject, keep its state to come back to, and prepare a state to move to.

-   ![](film:PathsHero)

    [**Paths**](paths.md)

    ---

    The curves a shape is made of: draw a path of your own, and find points along one.

</div>

## Kinds of mobjects

<div class="grid cards mx-cards" markdown>

-   ![](film:LinesAndArrows)

    [**Shapes**](shapes/index.md)

    ---

    Lines and arrows, circles and arcs, polygons, and shapes made from other shapes.

-   ![](film:AnnotationsHero)

    [**Annotations**](annotations.md)

    ---

    Braces, labels, frames, underlines and angle marks: what points at other mobjects.

-   ![](film:TextAndMathHero)

    [**Text and math**](text-and-math/index.md)

    ---

    Words, formulas and numbers, set by Typst inside ManimGX.

-   ![](film:GraphsHero)

    [**Graphs**](graphs/index.md)

    ---

    Axes, number lines and planes, the graphs of functions and data, vector fields.

-   ![](film:NetworksHero)

    [**Networks**](networks.md)

    ---

    Vertices joined by edges, laid out for you, which grow and change.

-   ![](film:MatricesAndTablesHero)

    [**Matrices and tables**](matrices-and-tables.md)

    ---

    Entries in rows and columns, between brackets or between lines.

-   ![](film:ImagesAndSvgHero)

    [**Images and SVG**](images-and-svg.md)

    ---

    Pictures from files or pixels, and drawings read from SVG files.

-   ![](film:PointCloudsHero)

    [**Point clouds**](point-clouds.md)

    ---

    Mobjects drawn as points, each a dot of its own color.

</div>

## The mobject

::: manimgx.Mobject
    options:
      heading_level: 3
      members: false

::: manimgx.Mobject.submobjects
    options:
      heading_level: 4

::: manimgx.Mobject.name
    options:
      heading_level: 4
