---
title: "Charts"
description: "Bar charts that grow and change, and the sample spaces of probability."
---

# Charts

```python fold title="The film's code"
import manimgx as m


class ChartsHero(m.Scene):
    def construct(self) -> None:
        chart = m.BarChart(
            [3, 5, 2, 6, 4], bar_names=["A", "B", "C", "D", "E"], y_range=[0, 8, 2]
        )
        self.play(m.Create(chart))
        self.play(chart.animate.change_bar_values([5, 2, 6, 3, 7]), run_time=2)
        self.wait()
```

A bar chart is axes with a bar for each value, which grow and shrink as the values change. A
sample space is a rectangle that stands for all the outcomes of a chance: divide it into
parts whose areas are their probabilities.

::: manimgx.BarChart
    options:
      heading_level: 2

::: manimgx.SampleSpace
    options:
      heading_level: 2
