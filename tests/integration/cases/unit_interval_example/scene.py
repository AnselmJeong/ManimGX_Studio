# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class UnitIntervalExample(m.Scene):
    def construct(self):
        ui = m.UnitInterval()
        self.add(ui)
        self.wait()
