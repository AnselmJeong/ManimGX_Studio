# Source: docs/source/tutorials/quickstart.rst
import manimgx as m


class TransformCycle(m.Scene):
    def construct(self):
        a = m.Circle()
        t1 = m.Square()
        t2 = m.Triangle()
        self.add(a)
        self.wait()
        for t in [t1, t2]:
            self.play(m.Transform(a, t))
