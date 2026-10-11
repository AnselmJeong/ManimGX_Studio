# Source: manim/constants.py
import manimgx as m


class DefaultWaitTimeConstant(m.Scene):
    def construct(self):
        dot = m.Dot()
        self.add(dot)
        self.wait(m.DEFAULT_WAIT_TIME)
