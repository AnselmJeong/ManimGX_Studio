# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VMobjectGetSubpathsExample(m.Scene):
    def construct(self):
        ring = m.Annulus(inner_radius=0.8, outer_radius=1.5, color=m.GREY)
        subpath_dots = m.Group()
        for chunk in ring.get_subpaths():
            subpath_dots.add(m.Dot(point=chunk[0], color=m.YELLOW, radius=0.06))
        self.add(ring, subpath_dots)
        self.wait()
