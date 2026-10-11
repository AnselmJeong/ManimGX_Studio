# Source: manim/mobject/logo.py
import manimgx as m


class DarkThemeBanner(m.Scene):
    def construct(self):
        banner = m.ManimBanner()
        self.play(banner.create())
        self.play(banner.expand())
        self.wait()
        self.play(m.Unwrite(banner))
