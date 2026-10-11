# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class RunTime(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)
        self.play(square.animate.shift(m.UP), run_time=3)
        self.wait(1)
