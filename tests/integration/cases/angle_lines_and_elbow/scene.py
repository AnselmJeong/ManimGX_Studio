# Source: manim/mobject/geometry/line.py
import manimgx as m


class AngleLinesAndElbow(m.Scene):
    def construct(self):
        line1 = m.Line(m.LEFT * 2, m.RIGHT * 2)
        line2 = m.Line(m.DOWN * 2, m.UP * 2)
        # Angle.get_lines exposes the source lines; elbow=True renders a
        # right-angle marker instead of an arc.
        angle = m.Angle(line1, line2, radius=0.6, elbow=True, color=m.YELLOW)
        readout = m.Text(f"lines={len(angle.get_lines())}", color=m.WHITE).scale(0.4)
        readout.next_to(angle, m.UR, buff=0.3)
        self.add(line1, line2, angle, readout)
        self.wait()
