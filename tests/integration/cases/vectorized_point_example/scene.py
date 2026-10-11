# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VectorizedPointExample(m.Scene):
    def construct(self):
        anchor = m.VectorizedPoint([2.0, 1.0, 0.0])
        marker = m.Dot(point=anchor.get_location(), color=m.RED, radius=0.1)
        anchor.set_location([-1.5, -0.5, 0.0])
        moved_marker = m.Dot(point=anchor.get_location(), color=m.YELLOW, radius=0.1)
        label = m.Text(
            f"w={anchor.width:.2f} h={anchor.height:.2f}", font_size=24
        ).to_edge(m.UP)
        self.add(marker, moved_marker, label)
        self.wait()
