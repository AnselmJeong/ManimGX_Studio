# Source: manim/animation/composition.py
import manimgx as m


class SuccessionExample(m.Scene):
    def construct(self):
        dot1 = m.Dot(point=m.LEFT * 2 + m.UP * 2, radius=0.16, color=m.BLUE)
        dot2 = m.Dot(point=m.LEFT * 2 + m.DOWN * 2, radius=0.16, color=m.MAROON)
        dot3 = m.Dot(point=m.RIGHT * 2 + m.DOWN * 2, radius=0.16, color=m.GREEN)
        dot4 = m.Dot(point=m.RIGHT * 2 + m.UP * 2, radius=0.16, color=m.YELLOW)
        self.add(dot1, dot2, dot3, dot4)

        self.play(
            m.Succession(
                dot1.animate.move_to(dot2),
                dot2.animate.move_to(dot3),
                dot3.animate.move_to(dot4),
                dot4.animate.move_to(dot1),
            )
        )
