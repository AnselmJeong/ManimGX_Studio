# Source: manim/animation/indication.py
import manimgx as m


class WigglePivotKwargsExample(m.Scene):
    def construct(self):
        square = m.Square(side_length=2).shift(m.RIGHT * 2)
        self.add(square)
        self.play(
            m.Wiggle(
                square,
                scale_value=1.4,
                rotation_angle=0.2,
                n_wiggles=4,
                scale_about_point=[0.0, 0.0, 0.0],
                rotate_about_point=[2.0, 1.0, 0.0],
                run_time=1.0,
            )
        )
