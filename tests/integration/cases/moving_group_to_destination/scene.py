# Source: docs/source/examples.rst
import manimgx as m


class MovingGroupToDestination(m.Scene):
    def construct(self):
        group = m.VGroup(
            m.Dot(m.LEFT),
            m.Dot(m.ORIGIN),
            m.Dot(m.RIGHT, color=m.RED),
            m.Dot(2 * m.RIGHT),
        ).scale(1.4)
        dest = m.Dot([4, 3, 0], color=m.YELLOW)
        self.add(group, dest)
        self.play(group.animate.shift(dest.get_center() - group[2].get_center()))
        self.wait(0.5)
