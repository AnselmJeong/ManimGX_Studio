# Source: manim/animation/updaters/update.py
import manimgx as m


class UpdateFromAlphaFuncExample(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)

        def slide(mob, alpha):
            mob.move_to([-2.0 + 4.0 * alpha, 0.0, 0.0])

        self.play(m.UpdateFromAlphaFunc(square, slide, run_time=1.0))
