# Source: docs/source/examples.rst
import manimgx as m


class BraceAnnotation(m.Scene):
    def construct(self):
        dot = m.Dot([-2, -1, 0])
        dot2 = m.Dot([2, 1, 0])
        line = m.Line(dot.get_center(), dot2.get_center()).set_color(m.ORANGE)
        b1 = m.Brace(line)
        b1text = b1.get_text("Horizontal distance")
        b2 = m.Brace(line, direction=line.copy().rotate(m.PI / 2).get_unit_vector())
        b2text = b2.get_tex("x-x_1")
        self.add(line, dot, dot2, b1, b2, b1text, b2text)
        self.wait()
