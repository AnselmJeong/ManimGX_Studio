# Source: manim/mobject/geometry/arc.py
import manimgx as m


class SeveralArcPolygons(m.Scene):
    def construct(self):
        a = [0, 0, 0]
        b = [2, 0, 0]
        c = [0, 2, 0]
        ap1 = m.ArcPolygon(a, b, c, radius=2)
        ap2 = m.ArcPolygon(a, b, c, angle=45 * m.DEGREES)
        ap3 = m.ArcPolygon(a, b, c, arc_config={"radius": 1.7, "color": m.RED})
        ap4 = m.ArcPolygon(
            a,
            b,
            c,
            color=m.RED,
            fill_opacity=1,
            arc_config=[
                {"radius": 1.7, "color": m.RED},
                {"angle": 20 * m.DEGREES, "color": m.BLUE},
                {"radius": 1},
            ],
        )
        ap_group = m.VGroup(ap1, ap2, ap3, ap4).arrange()
        self.play(*[m.Create(ap) for ap in [ap1, ap2, ap3, ap4]])
        self.wait()
