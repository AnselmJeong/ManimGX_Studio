# Source: manimgx API coverage (CE 0.21 `Scene.remove_updater`)
import manimgx as m


class SceneRemoveUpdaterExample(m.Scene):
    def construct(self):
        dot = m.Dot(3 * m.LEFT, color=m.YELLOW)
        self.add(dot)

        def drift(dt: float) -> None:
            dot.shift(3 * dt * m.RIGHT)

        self.add_updater(drift)
        self.wait(1)
        self.remove_updater(drift)
        self.wait(0.5)
