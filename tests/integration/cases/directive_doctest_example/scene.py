# Source: manim/utils/docbuild/manim_directive.py
import manimgx as m

dot = m.Dot(color=m.RED)


class DirectiveDoctestExample(m.Scene):
    def construct(self):
        self.play(m.Create(dot))
