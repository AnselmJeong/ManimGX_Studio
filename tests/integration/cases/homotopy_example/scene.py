# Source: manim/animation/movement.py
import numpy as np

import manimgx as m


class HomotopyExample(m.Scene):
    def construct(self):
        square = m.Square()

        def homotopy(x, y, z, t):
            if t <= 0.25:
                progress = t / 0.25
                return (
                    x,
                    y + progress * 0.2 * np.sin(x),
                    z,
                )
            wave_progress = (t - 0.25) / 0.75
            return (
                x,
                y + 0.2 * np.sin(x + 10 * wave_progress),
                z,
            )

        self.play(m.Homotopy(homotopy, square, rate_func=m.linear, run_time=2))
