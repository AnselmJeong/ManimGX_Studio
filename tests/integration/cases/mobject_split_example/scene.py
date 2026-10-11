# Source: manimgx API coverage (CE 0.21 `Mobject.split`)
import manimgx as m


class MobjectSplitExample(m.Scene):
    def construct(self):
        group = m.VGroup(m.Circle(), m.Square(), m.Triangle()).arrange(m.RIGHT, buff=1)
        self.add(group)
        colors = [m.RED, m.GREEN, m.BLUE]
        self.play(
            *(part.animate.set_color(c) for part, c in zip(group.split(), colors))
        )
