# Source: manim/mobject/value_tracker.py
import manimgx as m


class ValueTrackerExample(m.Scene):
    def construct(self):
        number_line = m.NumberLine()
        pointer = m.Vector(m.DOWN)
        label = m.MathTex("x").add_updater(lambda mobj: mobj.next_to(pointer, m.UP))

        tracker = m.ValueTracker(0)
        pointer.add_updater(
            lambda mobj: mobj.next_to(number_line.n2p(tracker.get_value()), m.UP)
        )
        self.add(number_line, pointer, label)
        tracker += 1.5
        self.wait(1)
        tracker -= 4
        self.wait(0.5)
        self.play(tracker.animate.set_value(5))
        self.wait(0.5)
        self.play(tracker.animate.set_value(3))
        self.play(tracker.animate.increment_value(-2))
        self.wait(0.5)
