# Source: manim/animation/updaters/update.py
import manimgx as m


class MaintainPositionRelativeToExample(m.Scene):
    def construct(self):
        leader = m.Square().set_color(m.BLUE)
        follower = m.Circle().set_color(m.YELLOW).next_to(leader, m.RIGHT, buff=0.5)
        self.add(leader, follower)
        self.play(
            leader.animate.shift(m.UP * 1.5),
            m.MaintainPositionRelativeTo(follower, leader),
            run_time=1.0,
        )
