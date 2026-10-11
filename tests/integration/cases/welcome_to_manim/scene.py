# Source: manim/animation/updaters/mobject_update_utils.py
import manimgx as m


class WelcomeToManim(m.Scene):
    def construct(self):
        words = m.Text("Welcome to")
        banner = m.ManimBanner().scale(0.5)
        m.VGroup(words, banner).arrange(m.DOWN)

        m.turn_animation_into_updater(m.Write(words, run_time=0.9))
        self.add(words)
        self.wait(0.5)
        self.play(banner.expand(), run_time=0.5)
