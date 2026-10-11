# Source: manim/animation/updaters/mobject_update_utils.py
import manimgx as m


class TurnAnimationIntoUpdaterDelayExample(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)
        m.turn_animation_into_updater(
            m.Rotate(square, angle=m.PI / 2, run_time=0.5), delay=0.4
        )
        self.wait(1.0)
