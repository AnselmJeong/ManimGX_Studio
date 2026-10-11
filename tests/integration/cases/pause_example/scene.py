# Source: manimgx API coverage (CE 0.21 `Scene.pause`)
import manimgx as m


class PauseExample(m.Scene):
    def construct(self):
        circle = m.Circle(color=m.PINK)
        self.play(m.Create(circle))
        self.pause(0.5)
        self.play(circle.animate.shift(2 * m.RIGHT))
