# Source: manim/animation/composition.py
import manimgx as m


class LaggedStartMapExample(m.Scene):
    def construct(self):
        title = m.Tex("LaggedStartMap").to_edge(m.UP, buff=m.LARGE_BUFF)
        dots = m.VGroup(*[m.Dot(radius=0.16) for _ in range(35)]).arrange_in_grid(
            rows=5, cols=7, buff=m.MED_LARGE_BUFF
        )
        self.add(dots, title)

        # Animate yellow ripple effect
        for mob in dots, title:
            self.play(
                m.LaggedStartMap(
                    m.ApplyMethod,
                    mob,
                    lambda x: (x.set_color, m.YELLOW),
                    lag_ratio=0.1,
                    run_time=2,
                )
            )
