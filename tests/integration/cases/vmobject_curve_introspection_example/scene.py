# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VMobjectCurveIntrospectionExample(m.Scene):
    def construct(self):
        polygon = m.RegularPolygon(n=5, color=m.YELLOW).scale(1.5)
        labels = m.Group()
        for i in range(polygon.get_num_curves()):
            points = polygon.get_nth_curve_points(i)
            midpoint = (points[0] + points[3]) * 0.5
            labels.add(m.Dot(point=midpoint, color=m.WHITE, radius=0.05))
        last = m.Dot(point=polygon.get_last_point(), color=m.RED, radius=0.08)
        title = m.Text(
            f"curves={polygon.get_num_curves()} len={polygon.get_arc_length():.2f}",
            font_size=24,
        ).to_edge(m.UP)
        self.add(polygon, labels, last, title)
        self.wait()
