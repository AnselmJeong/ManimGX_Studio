# Source: manim/animation/indication.py
import manimgx as m


class BlinkingExample(m.Scene):
    def construct(self):
        text = m.Text("Blinking").scale(1.5)
        self.add(text)
        self.play(m.Blink(text, blinks=3))
