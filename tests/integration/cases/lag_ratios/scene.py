# Source: manim/animation/animation.py
import manimgx as m


class LagRatios(m.Scene):
    def construct(self):
        ratios = [0, 0.1, 0.5, 1, 2]  # demonstrated lag_ratios

        # Create dot groups
        group = m.VGroup(*[m.Dot() for _ in range(4)]).arrange_submobjects()
        groups = m.VGroup(*[group.copy() for _ in ratios]).arrange_submobjects(buff=1)
        self.add(groups)

        # Label groups
        self.add(m.Text("lag_ratio = ", font_size=36).next_to(groups, m.UP, buff=1.5))
        for group, ratio in zip(groups, ratios):
            self.add(m.Text(str(ratio), font_size=36).next_to(group, m.UP))

        # Animate groups with different lag_ratios
        self.play(
            m.AnimationGroup(
                *[
                    group.animate(lag_ratio=ratio, run_time=1.5).shift(m.DOWN * 2)
                    for group, ratio in zip(groups, ratios)
                ]
            )
        )

        # lag_ratio also works recursively on nested submobjects:
        self.play(groups.animate(run_time=1, lag_ratio=0.1).shift(m.UP * 2))
