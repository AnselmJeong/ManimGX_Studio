# Source: manim/mobject/mobject.py
import manimgx as m


class DtUpdater(m.Scene):
    def construct(self):
        square = m.Square()

        # Let the square rotate 90° per second
        square.add_updater(lambda mobject, dt: mobject.rotate(dt * 90 * m.DEGREES))
        self.add(square)
        self.wait(2)
