# Source: manim/animation/indication.py
import manimgx as m


class TimeWidthValues(m.Scene):
    def construct(self):
        p = m.RegularPolygon(5, color=m.DARK_GRAY, stroke_width=6).scale(3)
        lbl = m.Tex("")
        self.add(p, lbl)
        p = p.copy().set_color(m.BLUE)
        for time_width in [0.2, 0.5, 1, 2]:
            lbl.become(m.Tex(rf"\texttt{{time\_width={{{{{time_width:.1f}}}}}}}"))
            self.play(
                m.ShowPassingFlash(
                    p.copy().set_color(m.BLUE), run_time=2, time_width=time_width
                )
            )
