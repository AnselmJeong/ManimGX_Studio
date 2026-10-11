# Source: manim/mobject/logo.py
import manimgx as m


class LightThemeBanner(m.Scene):
    def construct(self):
        self.camera.background_color = "#ece6e2"
        banner = m.ManimBanner(dark_theme=False)
        self.play(banner.create())
        self.play(banner.expand())
        self.wait()
        self.play(m.Unwrite(banner))
