# Source: manim/mobject/mobject.py
import manimgx as m


class NextToUpdater(m.Scene):
    def construct(self):
        def update_label(mobject):
            mobject.set_value(dot.get_center()[0])
            mobject.next_to(dot)

        dot = m.Dot(m.RIGHT * 3)
        label = m.DecimalNumber()
        label.add_updater(update_label)
        self.add(dot, label)

        self.play(
            m.Rotating(
                dot,
                angle=m.TAU,
                about_point=m.ORIGIN,
                run_time=m.TAU,
                rate_func=m.linear,
            )
        )
