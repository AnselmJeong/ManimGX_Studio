# Source: docs/source/tutorials/building_blocks.rst
import numpy as np

import manimgx as m


class ExampleRotation(m.Scene):
    def construct(self):
        self.camera.background_color = m.WHITE
        m1a = m.Square().set_color(m.RED).shift(m.LEFT)
        m1b = m.Circle().set_color(m.RED).shift(m.LEFT)
        m2a = m.Square().set_color(m.BLUE).shift(m.RIGHT)
        m2b = m.Circle().set_color(m.BLUE).shift(m.RIGHT)

        points = m2a.points
        points = np.roll(points, int(len(points) / 4), axis=0)
        m2a.points = points

        self.play(m.Transform(m1a, m1b), m.Transform(m2a, m2b), run_time=1)
