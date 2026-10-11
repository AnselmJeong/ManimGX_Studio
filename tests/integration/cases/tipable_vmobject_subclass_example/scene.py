# Source: manim/mobject/geometry/arc.py
import manimgx as m


class TipableVMobjectSubclassExample(m.Scene):
    def construct(self):
        # ``TipableVMobject`` is the CE base for shapes that can mount a tip.
        # manimgx mirrors the surface so scene authors writing custom
        # ``add_tip``-capable shapes can reuse the same import path.
        assert issubclass(m.Arrow, m.TipableVMobject) or hasattr(
            m.TipableVMobject, "add_tip"
        )

        arrow = m.Arrow(m.LEFT * 2, m.RIGHT * 2, buff=0, color=m.YELLOW)
        readout = m.Text(f"has_tip={arrow.has_tip()}", color=m.WHITE).scale(0.4)
        readout.next_to(arrow, m.DOWN, buff=0.3)
        self.add(arrow, readout)
        self.wait()
