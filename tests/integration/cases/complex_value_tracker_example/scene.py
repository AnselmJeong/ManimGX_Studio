# Source: manim/mobject/value_tracker.py
import manimgx as m


class ComplexValueTrackerExample(m.Scene):
    def construct(self):
        tracker = m.ComplexValueTracker(-2 + 1j)
        dot = m.Dot().add_updater(lambda x: x.move_to(tracker.points))

        self.add(m.NumberPlane(), dot)

        self.play(tracker.animate.set_value(3 + 2j))
        self.play(tracker.animate.set_value(tracker.get_value() * 1j))
        self.play(tracker.animate.set_value(tracker.get_value() - 2j))
        self.play(tracker.animate.set_value(tracker.get_value() / (-2 + 3j)))
