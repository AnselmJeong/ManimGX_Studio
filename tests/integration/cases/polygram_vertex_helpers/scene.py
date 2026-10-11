# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class PolygramVertexHelpers(m.Scene):
    def construct(self):
        poly = m.Polygram(
            [[-2.0, -1.0, 0.0], [2.0, -1.0, 0.0], [0.0, 2.0, 0.0]],
            color=m.BLUE,
        )
        # CE-parity readers — splash the vertex count somewhere visible.
        groups = poly.get_vertex_groups()
        verts = poly.get_vertices()
        readout = m.Text(
            f"groups={len(groups)} verts={len(verts)}", color=m.YELLOW
        ).scale(0.4)
        readout.next_to(poly, m.DOWN, buff=0.3)
        self.add(poly, readout)
        self.wait()
