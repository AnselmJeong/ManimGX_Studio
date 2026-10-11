# Source: manim/animation/transform_matching_parts.py
import manimgx as m


class Anagram(m.Scene):
    def construct(self):
        src = m.Text("the morse code")
        tar = m.Text("here come dots")
        self.play(m.Write(src))
        self.wait(0.5)
        self.play(m.TransformMatchingShapes(src, tar, path_arc=m.PI / 2))
        self.wait(0.5)
