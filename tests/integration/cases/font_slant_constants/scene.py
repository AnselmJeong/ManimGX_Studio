# Source: manim/constants.py
import manimgx as m


class FontSlantConstants(m.Scene):
    def construct(self):
        slants = [m.NORMAL, m.ITALIC, m.OBLIQUE]
        labels = m.VGroup(*[m.Text(s, slant=s, font_size=18) for s in slants])
        labels.arrange(m.DOWN, buff=m.SMALL_BUFF)
        self.add(labels)
        self.wait()
