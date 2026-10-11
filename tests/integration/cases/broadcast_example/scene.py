# Source: manim/animation/specialized.py
import manimgx as m


class BroadcastExample(m.Scene):
    def construct(self):
        mob = m.Circle(radius=4, color=m.TEAL_A)
        self.play(m.Broadcast(mob))
