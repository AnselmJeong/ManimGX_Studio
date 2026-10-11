# Source: manim/mobject/geometry/line.py
import numpy as np

import manimgx as m


class LineGeometryHelpers(m.Scene):
    def construct(self):
        line = m.Line(np.array([-2.0, -1.0, 0.0]), np.array([2.0, 1.0, 0.0]))
        # set_angle aligns the line to a target angle.
        line.set_angle(np.pi / 4)
        self.add(line)

        # get_angle / get_slope readouts.
        angle = line.get_angle()
        slope = line.get_slope()
        label_a = m.Text(f"angle={angle:.2f}", color=m.YELLOW).scale(0.4)
        label_s = m.Text(f"slope={slope:.2f}", color=m.GREEN).scale(0.4)
        label_a.next_to(line, m.UP, buff=0.4)
        label_s.next_to(line, m.DOWN, buff=0.4)

        # get_projection of a probe point onto the line.
        proj = line.get_projection(np.array([0.0, 1.5, 0.0]))
        proj_dot = m.Dot(point=proj, color=m.RED, radius=0.08)

        # set_path_arc bends the line afterwards.
        bent = m.Line(
            np.array([-2.5, -2.0, 0.0]), np.array([2.5, -2.0, 0.0]), color=m.BLUE
        )
        bent.set_path_arc(np.pi / 2)

        self.add(label_a, label_s, proj_dot, bent)
        self.wait()
