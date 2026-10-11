# Source: manim/scene/scene.py
import manimgx as m


class SceneWaitDurationKwarg(m.Scene):
    def construct(self):
        circle = m.Circle()
        self.play(m.Create(circle))
        self.wait(duration=0.2)
