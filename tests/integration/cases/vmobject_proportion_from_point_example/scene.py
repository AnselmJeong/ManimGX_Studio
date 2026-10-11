# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VMobjectProportionFromPointExample(m.Scene):
    def construct(self):
        circle = m.Circle(radius=2.0, color=m.WHITE)
        sample = circle.point_from_proportion(0.4)
        proportion = circle.proportion_from_point(sample)
        marker = m.Dot(point=sample, color=m.RED, radius=0.1)
        label = m.Text(f"t={proportion:.2f}", font_size=24).next_to(marker, m.UP)
        self.add(circle, marker, label)
        self.wait()
