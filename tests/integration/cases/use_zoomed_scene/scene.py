# Source: manim/scene/zoomed_scene.py
import manimgx as m


class UseZoomedScene(m.ZoomedScene):
    def construct(self):
        dot = m.Dot().set_color(m.GREEN)
        self.add(dot)
        self.wait(1)
        self.activate_zooming(animate=False)
        self.wait(1)
        self.play(dot.animate.shift(m.LEFT))
