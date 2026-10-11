# Source: manim/mobject/types/vectorized_mobject.py
#
# Regression: any VMobject containing an arc segment cubicizes that arc to
# multiple cubic Béziers (~8 cubics for a single 180° arc, plus the same
# expansion for each 90° quadrant of a Circle). `get_num_curves` counts
# cubics, so `get_nth_curve_length(i)` must agree for every `i in
# range(get_num_curves())` — otherwise iterating curves to sum lengths
# IndexErrors.

import manimgx as m


class VMobjectArcCurveLengthExample(m.Scene):
    def construct(self):
        arc = m.Arc(radius=1.5, start_angle=0, angle=m.PI, color=m.YELLOW)
        n = arc.get_num_curves()
        lengths = [arc.get_nth_curve_length(i) for i in range(n)]
        total = sum(lengths)
        sampled_total = arc.get_arc_length(sample_points_per_curve=20)
        label = m.Text(
            f"n={n} sum={total:.2f} sampled={sampled_total:.2f}",
            font_size=24,
        ).to_edge(m.UP)
        self.add(arc, label)
        self.wait()
