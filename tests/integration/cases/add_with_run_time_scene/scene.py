# Source: manim/animation/animation.py
import manimgx as m


class AddWithRunTimeScene(m.Scene):
    def construct(self):
        # A 5x5 grid of circles
        circles = m.VGroup(*[m.Circle(radius=0.5) for _ in range(25)]).arrange_in_grid(
            5, 5
        )

        self.play(
            m.Succession(
                # Add a run_time of 0.2 to wait for 0.2 seconds after
                # adding the circle, instead of using Wait(0.2) after Add!
                *[m.Add(circle, run_time=0.2) for circle in circles],
                rate_func=m.smooth,
            )
        )
        self.wait()
