# Source: manim/mobject/text/tex_mobject.py
import manimgx as m


class BulletedListFadeAllButExample(m.Scene):
    def construct(self):
        items = m.BulletedList("First", "Second", "Third")
        items.fade_all_but(1)
        self.play(m.FadeIn(items))
        self.wait(0.2)
