# Source: manim/animation/speedmodifier.py
import manimgx as m


class SpeedModifierUpdaterExample2(m.Scene):
    def construct(self):
        a = m.Dot().shift(m.LEFT * 4)
        self.add(a)

        m.ChangeSpeed.add_updater(a, lambda x, dt: x.shift(m.RIGHT * 4 * dt))
        self.wait()
        self.play(
            m.ChangeSpeed(
                m.Wait(),
                speedinfo={1: 0},
                affects_speed_updaters=True,
            )
        )
