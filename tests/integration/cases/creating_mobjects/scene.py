# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class CreatingMobjects(m.Scene):
    def construct(self):
        circle = m.Circle()
        self.add(circle)
        self.wait(1)
        self.remove(circle)
        self.wait(1)
