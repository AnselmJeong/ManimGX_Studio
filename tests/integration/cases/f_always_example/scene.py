# Source: manim/animation/updaters/mobject_update_utils.py
import manimgx as m


class FAlwaysExample(m.Scene):
    def construct(self):
        leader = m.Square().set_color(m.BLUE)
        follower = m.Circle().set_color(m.YELLOW)
        self.add(leader, follower)
        m.f_always(follower.move_to, leader.get_right)
        self.play(leader.animate.shift(m.UP * 2 + m.RIGHT), run_time=1.0)
