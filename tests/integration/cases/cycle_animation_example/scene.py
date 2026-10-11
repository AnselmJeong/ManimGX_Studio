# Source: manim/animation/updaters/mobject_update_utils.py
import manimgx as m


class CycleAnimationExample(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)
        cycled = m.Rotate(square, angle=m.PI, run_time=0.5)
        m.cycle_animation(cycled)
        self.wait(1.0)
