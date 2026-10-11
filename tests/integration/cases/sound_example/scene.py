# Source: manim/scene/scene.py
from pathlib import Path

import manimgx as m

CLICK = str(Path(__file__).with_name("click.wav"))


class SoundExample(m.Scene):
    # Source of sound under Creative Commons 0 License. https://freesound.org/people/Druminfected/sounds/250551/
    def construct(self):
        dot = m.Dot().set_color(m.GREEN)
        self.add_sound(CLICK)
        self.add(dot)
        self.wait()
        self.add_sound(CLICK)
        dot.set_color(m.BLUE)
        self.wait()
        self.add_sound(CLICK)
        dot.set_color(m.RED)
        self.wait()
