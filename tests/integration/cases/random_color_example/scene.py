# Source: manimgx API coverage (CE 0.21 `random_color`)
import manimgx as m


class RandomColorExample(m.Scene):
    def construct(self):
        dots = m.VGroup(
            *(m.Dot(radius=0.35, color=m.random_color()) for _ in range(12))
        )
        dots.arrange_in_grid(3, 4, buff=0.7)
        self.play(m.LaggedStart(*(m.GrowFromCenter(d) for d in dots), lag_ratio=0.1))
