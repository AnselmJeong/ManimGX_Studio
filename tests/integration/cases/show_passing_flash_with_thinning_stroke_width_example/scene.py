# Source: manim/animation/indication.py
import manimgx as m


class ShowPassingFlashWithThinningStrokeWidthExample(m.Scene):
    def construct(self):
        line = m.Line(m.LEFT * 3, m.RIGHT * 3, stroke_width=10).set_color(m.YELLOW)
        self.add(line)
        self.play(
            m.ShowPassingFlashWithThinningStrokeWidth(
                line, n_segments=8, time_width=0.5, run_time=1.0
            )
        )
