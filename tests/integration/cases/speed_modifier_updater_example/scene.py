# Source: manim/animation/speedmodifier.py
import manimgx as m


class SpeedModifierUpdaterExample(m.Scene):
    def construct(self):
        a = m.Dot().shift(m.LEFT * 4)
        self.add(a)

        m.ChangeSpeed.add_updater(a, lambda x, dt: x.shift(m.RIGHT * 4 * dt))
        self.play(
            m.ChangeSpeed(
                m.Wait(2),
                speedinfo={0.4: 1, 0.5: 0.2, 0.8: 0.2, 1: 1},
                affects_speed_updaters=True,
            )
        )
