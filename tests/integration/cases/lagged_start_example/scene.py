# Source: manim/animation/composition.py
import manimgx as m


class LaggedStartExample(m.Scene):
    def construct(self):
        title = m.Text("lag_ratio = 0.25").to_edge(m.UP)

        dot1 = m.Dot(point=m.LEFT * 2 + m.UP, radius=0.16)
        dot2 = m.Dot(point=m.LEFT * 2, radius=0.16)
        dot3 = m.Dot(point=m.LEFT * 2 + m.DOWN, radius=0.16)
        line_25 = m.DashedLine(
            start=m.LEFT + m.UP * 2, end=m.LEFT + m.DOWN * 2, color=m.RED
        )
        label = m.Text("25%", font_size=24).next_to(line_25, m.UP)
        self.add(title, dot1, dot2, dot3, line_25, label)

        self.play(
            m.LaggedStart(
                dot1.animate.shift(m.RIGHT * 4),
                dot2.animate.shift(m.RIGHT * 4),
                dot3.animate.shift(m.RIGHT * 4),
                lag_ratio=0.25,
                run_time=4,
            )
        )
