# Source: docs/source/examples.rst
import manimgx as m


class VectorArrow(m.Scene):
    def construct(self):
        dot = m.Dot(m.ORIGIN)
        arrow = m.Arrow(m.ORIGIN, [2, 2, 0], buff=0)
        numberplane = m.NumberPlane()
        origin_text = m.Text("(0, 0)").next_to(dot, m.DOWN)
        tip_text = m.Text("(2, 2)").next_to(arrow.get_end(), m.RIGHT)
        self.add(numberplane, dot, arrow, origin_text, tip_text)
        self.wait()
