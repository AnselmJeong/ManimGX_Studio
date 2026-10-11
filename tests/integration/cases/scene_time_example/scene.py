# Source: manimgx API coverage (CE 0.21 `Scene.time`)
import manimgx as m


class SceneTimeExample(m.Scene):
    def construct(self):
        clock = m.DecimalNumber(0, num_decimal_places=2).scale(2)
        clock.add_updater(lambda d: d.set_value(self.time))
        self.add(clock)
        self.wait(1)
        self.play(clock.animate.shift(m.UP))
        self.wait(0.5)
