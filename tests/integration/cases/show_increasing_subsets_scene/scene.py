# Source: manim/animation/creation.py
import manimgx as m


class ShowIncreasingSubsetsScene(m.Scene):
    def construct(self):
        p = m.VGroup(m.Dot(), m.Square(), m.Triangle())
        self.add(p)
        self.play(m.ShowIncreasingSubsets(p))
        self.wait()
