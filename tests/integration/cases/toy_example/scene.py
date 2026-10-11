# Source: docs/source/guides/deep_dive.rst
import manimgx as m


class ToyExample(m.Scene):
    def construct(self):
        orange_square = m.Square(color=m.ORANGE, fill_opacity=0.5)
        blue_circle = m.Circle(color=m.BLUE, fill_opacity=0.5)
        self.add(orange_square)
        self.play(m.ReplacementTransform(orange_square, blue_circle, run_time=3))
        small_dot = m.Dot()
        small_dot.add_updater(lambda mob: mob.next_to(blue_circle, m.DOWN))
        self.play(m.Create(small_dot))
        self.play(blue_circle.animate.shift(m.RIGHT))
        self.wait()
        self.play(m.FadeOut(blue_circle, small_dot))
