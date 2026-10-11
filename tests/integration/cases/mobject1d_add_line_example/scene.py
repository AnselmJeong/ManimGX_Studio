# Source: manim/mobject/types/point_cloud_mobject.py
import manimgx as m


class Mobject1DAddLineExample(m.Scene):
    def construct(self):
        cloud = m.Mobject1D(density=30)
        cloud.add_line(m.LEFT * 2, m.RIGHT * 2, color=m.BLUE)
        cloud.add_line(m.DOWN * 1.5, m.UP * 1.5, color=m.YELLOW)
        self.add(cloud)
        self.wait()
