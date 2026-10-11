# Source: manim/animation/indication.py
import manimgx as m


class ApplyingWaves(m.Scene):
    def construct(self):
        tex = m.Tex("WaveWaveWaveWaveWave").scale(2)
        self.play(m.ApplyWave(tex))
        self.play(m.ApplyWave(tex, direction=m.RIGHT, time_width=0.5, amplitude=0.3))
        self.play(m.ApplyWave(tex, rate_func=m.linear, ripples=4))
