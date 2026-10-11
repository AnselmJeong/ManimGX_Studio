# Source: manim/mobject/geometry/line.py
import manimgx as m


class DashedLineHandles(m.Scene):
    def construct(self):
        dl = m.DashedLine(m.LEFT * 3, m.RIGHT * 3, color=m.WHITE)
        # CE-parity helpers: peek at the first/last interior handle points.
        first = dl.get_first_handle()
        last = dl.get_last_handle()
        marker_first = m.Dot(point=first, color=m.YELLOW, radius=0.08)
        marker_last = m.Dot(point=last, color=m.RED, radius=0.08)
        self.add(dl, marker_first, marker_last)
        self.wait()
