# Source: manim/animation/movement.py
import manimgx as m


class ComplexHomotopyExample(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)
        self.play(
            m.ComplexHomotopy(
                lambda z, t: z * (1 + 0.6 * t),
                square,
                run_time=1.0,
            )
        )
