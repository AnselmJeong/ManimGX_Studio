# Source: manim/mobject/geometry/arc.py
import numpy as np

import manimgx as m


class ArcCenterAndStopAngle(m.Scene):
    def construct(self):
        # Arc(arc_center=) places the arc at a specific center.
        arc_kw = m.Arc(
            radius=1.0,
            start_angle=0,
            angle=np.pi,
            arc_center=np.array([-2.0, 0.0, 0.0]),
            color=m.BLUE,
        )

        # move_arc_center_to shifts the arc afterwards.
        arc_moved = m.Arc(radius=1.0, start_angle=0, angle=np.pi, color=m.YELLOW)
        arc_moved.move_arc_center_to(np.array([2.0, 0.0, 0.0]))

        # stop_angle returns the angle of the trailing endpoint.
        label = m.Text(f"stop={arc_kw.stop_angle():.2f}", color=m.WHITE).scale(0.4)
        label.next_to(arc_kw, m.DOWN)

        self.add(arc_kw, arc_moved, label)
        self.wait()
