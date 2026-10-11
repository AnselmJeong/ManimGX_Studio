# Source: manim/animation/changing.py
import manimgx as m


class TracedPathExample(m.Scene):
    def construct(self):
        circ = m.Circle(color=m.RED).shift(4 * m.LEFT)
        dot = m.Dot(color=m.RED).move_to(circ.get_start())
        rolling_circle = m.VGroup(circ, dot)
        trace = m.TracedPath(circ.get_start)
        rolling_circle.add_updater(lambda m: m.rotate(-0.3))
        self.add(trace, rolling_circle)
        self.play(
            rolling_circle.animate.shift(8 * m.RIGHT),
            run_time=4,
            rate_func=m.linear,
        )
