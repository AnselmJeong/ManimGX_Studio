# Source: manim/animation/updaters/mobject_update_utils.py
import manimgx as m


class AssertIsMobjectMethodExample(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)
        # Calling the assertion as scene authors would when defining a
        # custom updater helper — guards against accidentally passing a
        # free function.
        m.assert_is_mobject_method(square.move_to)
        self.wait(0.5)
