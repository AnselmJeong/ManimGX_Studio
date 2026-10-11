# Source: manim/animation/indication.py
import manimgx as m


class FlashOnCircle(m.Scene):
    def construct(self):
        radius = 2
        circle = m.Circle(radius)
        self.add(circle)
        self.play(
            m.Flash(
                circle,
                line_length=1,
                num_lines=30,
                color=m.RED,
                flash_radius=radius + m.SMALL_BUFF,
                time_width=0.3,
                run_time=2,
                rate_func=m.rush_from,
            )
        )
