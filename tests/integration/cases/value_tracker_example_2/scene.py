# Source: manim/mobject/value_tracker.py
import manimgx as m


class ValueTrackerExample(m.Scene):
    def construct(self):
        tracker = m.ValueTracker(0)
        label = m.Dot(radius=3)

        def update_label(dot: m.Dot, dt: float) -> None:
            tracker.increment_value(dt)
            dot.set_x(tracker.get_value())

        label.add_updater(update_label)
        self.add(label)
        self.wait(2)
