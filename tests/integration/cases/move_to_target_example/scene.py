# Source: manim/animation/transform.py
import manimgx as m


class MoveToTargetExample(m.Scene):
    def construct(self):
        c = m.Circle()

        c.generate_target()
        assert c.target is not None
        c.target.set_fill(color=m.GREEN, opacity=0.5)
        c.target.shift(2 * m.RIGHT + m.UP).scale(0.5)

        self.add(c)
        self.play(m.MoveToTarget(c))
