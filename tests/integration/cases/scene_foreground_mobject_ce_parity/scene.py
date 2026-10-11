# Source: manim/scene/scene.py
import manimgx as m


class SceneForegroundMobjectCeParity(m.Scene):
    def construct(self):
        bg = m.Square(side_length=2, color=m.BLUE).set_fill(m.BLUE, opacity=1.0)
        fg = m.Circle(radius=0.5, color=m.RED).set_fill(m.RED, opacity=1.0)
        self.add(bg, fg)
        # CE-singular signature: ``add_foreground_mobject(mobject)`` —
        # accepts only one mobject. The plural form is variadic.
        self.add_foreground_mobject(fg)
        self.add_foreground_mobjects(bg)
        # Inverse: drop the foreground status so the mobjects render at default z.
        self.remove_foreground_mobject(fg)
        self.remove_foreground_mobjects(bg)
        self.wait(0.1)
