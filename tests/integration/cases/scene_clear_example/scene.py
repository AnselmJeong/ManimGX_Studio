# Source: manimgx API coverage (CE 0.21 `Scene.clear`)
import manimgx as m


class SceneClearExample(m.Scene):
    def construct(self):
        shapes = m.VGroup(m.Circle(), m.Square(), m.Triangle()).arrange(m.RIGHT, buff=1)
        self.play(m.Create(shapes))
        self.clear()
        self.wait(0.3)
        self.play(m.GrowFromCenter(m.Star(color=m.YELLOW, fill_opacity=1)))
