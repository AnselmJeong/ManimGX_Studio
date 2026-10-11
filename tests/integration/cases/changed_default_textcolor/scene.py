# Source: manim/mobject/mobject.py
import manimgx as m

m.config.background_color = m.WHITE


class ChangedDefaultTextcolor(m.Scene):
    def construct(self):
        m.Text.set_default(color=m.BLACK)
        self.add(m.Text("Changing default values is easy!"))

        # we revert the colour back to the default to prevent a bug in the docs.
        m.Text.set_default(color=m.WHITE)
