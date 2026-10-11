# Source: manim/mobject/geometry/tips.py
import numpy as np

import manimgx as m


class ArrowTipStartAngleKwargs(m.Scene):
    def construct(self):
        # CE-parity: every Arrow*Tip accepts ``start_angle=``. Default is PI.
        tip_a = m.ArrowCircleTip(start_angle=np.pi).shift(m.LEFT * 3)
        tip_b = m.ArrowSquareTip(start_angle=np.pi).shift(m.LEFT * 1)
        tip_c = m.ArrowTriangleTip(start_angle=np.pi).shift(m.RIGHT * 1)
        tip_d = m.StealthTip(start_angle=np.pi).shift(m.RIGHT * 3)
        self.add(tip_a, tip_b, tip_c, tip_d)
        self.wait()
