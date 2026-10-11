# Source: manim/mobject/value_tracker.py
import manimgx as m


class ValueTrackerDValueExample(m.Scene):
    def construct(self):
        tracker = m.ValueTracker(0.0)
        label = m.DecimalNumber(0, num_decimal_places=2)
        label.add_updater(lambda d: d.set_value(tracker.get_value()))
        self.add(label)
        self.play(tracker.animate.increment_value(d_value=3.5))
        self.wait()
