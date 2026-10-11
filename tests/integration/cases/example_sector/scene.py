# Source: manim/mobject/geometry/arc.py
import manimgx as m


class ExampleSector(m.Scene):
    def construct(self):
        sector = m.Sector(radius=2)
        sector2 = m.Sector(radius=2.5, angle=60 * m.DEGREES).move_to([-3, 0, 0])
        sector.set_color(m.RED)
        sector2.set_color(m.PINK)
        self.add(sector, sector2)
        self.wait()
