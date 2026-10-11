# Source: manim/mobject/geometry/line.py
import manimgx as m


class ArrowTipHelpers(m.Scene):
    def construct(self):
        arr = m.Arrow(m.LEFT * 2, m.RIGHT * 2, buff=0, color=m.BLUE)
        # CE-parity introspection: default tip length depends on arrow length.
        tip_len = arr.get_default_tip_length()
        # reset_normal_vector seeds the cached normal for downstream callers.
        arr.reset_normal_vector()
        normal = arr.get_normal_vector()

        label = m.Text(
            f"tip_len={tip_len:.2f}  normal_z={normal[2]:.0f}", color=m.YELLOW
        ).scale(0.4)
        label.next_to(arr, m.DOWN, buff=0.3)

        self.add(arr, label)
        self.wait()
