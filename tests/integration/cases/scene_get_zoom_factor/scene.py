# Source: manim/scene/zoomed_scene.py
import manimgx as m


class SceneGetZoomFactor(m.ZoomedScene):
    def __init__(self, **kwargs):
        super().__init__(zoom_factor=0.25, **kwargs)

    def construct(self):
        factor = self.get_zoom_factor()
        marker = m.Square(side_length=float(factor) * 4.0, color=m.YELLOW)
        self.add(marker)
        self.wait(0.1)
