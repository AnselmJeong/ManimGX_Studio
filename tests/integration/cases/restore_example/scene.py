# Source: manim/animation/transform.py
import manimgx as m


class RestoreExample(m.Scene):
    def construct(self):
        s = m.Square()
        s.save_state()
        self.play(m.FadeIn(s))
        self.play(
            s.animate.set_color(m.PURPLE).set_opacity(0.5).shift(2 * m.LEFT).scale(3)
        )
        self.play(s.animate.shift(5 * m.DOWN), m.Rotate(s, angle=m.PI / 4))
        self.wait()
        self.play(m.Restore(s), run_time=2)
