# Source: manimgx API coverage (CE 0.21 `Scene.wait_until`)
import manimgx as m


class WaitUntilExample(m.Scene):
    def construct(self):
        line = m.NumberLine(x_range=(-4, 4, 1), length=8)
        dot = m.Dot(line.n2p(-4), color=m.YELLOW)
        dot.add_updater(lambda d, dt: d.shift(2 * dt * m.RIGHT))
        self.add(line, dot)
        self.wait_until(lambda: dot.get_x() > 0.5, max_time=5)
        dot.clear_updaters()
        self.play(dot.animate.set_color(m.RED).scale(2))
