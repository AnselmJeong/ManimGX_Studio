# Source: manim/mobject/geometry/line.py
import manimgx as m


class GetValueExample(m.Scene):
    def construct(self):
        line1 = m.Line(m.LEFT + (1 / 3) * m.UP, m.RIGHT + (1 / 3) * m.DOWN)
        line2 = m.Line(m.DOWN + (1 / 3) * m.RIGHT, m.UP + (1 / 3) * m.LEFT)

        angle = m.Angle(line1, line2, radius=0.4)

        value = m.DecimalNumber(angle.get_value(degrees=True), unit=r"^{\circ}")
        value.next_to(angle, m.UR)

        self.add(line1, line2, angle, value)
        self.wait()
