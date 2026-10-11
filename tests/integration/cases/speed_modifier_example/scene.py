# Source: manim/animation/speedmodifier.py
import manimgx as m


class SpeedModifierExample(m.Scene):
    def construct(self):
        a = m.Dot().shift(m.LEFT * 4)
        b = m.Dot().shift(m.RIGHT * 4)
        self.add(a, b)
        self.play(
            m.ChangeSpeed(
                m.AnimationGroup(
                    a.animate(run_time=1).shift(m.RIGHT * 8),
                    b.animate(run_time=1).shift(m.LEFT * 8),
                ),
                speedinfo={0.3: 1, 0.4: 0.1, 0.6: 0.1, 1: 1},
                rate_func=m.linear,
            )
        )
