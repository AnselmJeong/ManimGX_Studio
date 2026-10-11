# Source: manim/mobject/geometry/labeled.py
import manimgx as m


class LabeledPolygramExample(m.Scene):
    def construct(self):
        # Define Rings
        ring1 = [
            [-3.8, -2.4, 0],
            [-2.4, -2.5, 0],
            [-1.3, -1.6, 0],
            [-0.2, -1.7, 0],
            [1.7, -2.5, 0],
            [2.9, -2.6, 0],
            [3.5, -1.5, 0],
            [4.9, -1.4, 0],
            [4.5, 0.2, 0],
            [4.7, 1.6, 0],
            [3.5, 2.4, 0],
            [1.1, 2.5, 0],
            [-0.1, 0.9, 0],
            [-1.2, 0.5, 0],
            [-1.6, 0.7, 0],
            [-1.4, 1.9, 0],
            [-2.6, 2.6, 0],
            [-4.4, 1.2, 0],
            [-4.9, -0.8, 0],
            [-3.8, -2.4, 0],
        ]
        ring2 = [
            [0.2, -1.2, 0],
            [0.9, -1.2, 0],
            [1.4, -2.0, 0],
            [2.1, -1.6, 0],
            [2.2, -0.5, 0],
            [1.4, 0.0, 0],
            [0.4, -0.2, 0],
            [0.2, -1.2, 0],
        ]
        ring3 = [[-2.7, 1.4, 0], [-2.3, 1.7, 0], [-2.8, 1.9, 0], [-2.7, 1.4, 0]]

        # Create Polygons (for reference)
        p1 = m.Polygon(*ring1, fill_opacity=0.75)
        p2 = m.Polygon(*ring2, fill_color=m.BLACK, fill_opacity=1)
        p3 = m.Polygon(*ring3, fill_color=m.BLACK, fill_opacity=1)

        # Create Labeled Polygram
        polygram = m.LabeledPolygram(
            *[ring1, ring2, ring3],
            label=m.Text("Pole", font="sans-serif"),
            precision=0.01,
        )

        # Display Circle (for reference)
        circle = m.Circle(radius=polygram.radius, color=m.WHITE).move_to(polygram.pole)

        self.add(p1, p2, p3)
        self.add(polygram)
        self.add(circle)
        self.wait()
