# Source: manim/constants.py
import manimgx as m


class CapStyleVariants(m.Scene):
    def construct(self):
        arcs = m.VGroup(
            *[
                m.Arc(
                    radius=1,
                    start_angle=0,
                    angle=m.TAU / 4,
                    stroke_width=20,
                    color=m.GREEN,
                    cap_style=cap_style,
                )
                for cap_style in m.CapStyleType
            ]
        )
        arcs.arrange(m.RIGHT, buff=1)
        self.add(arcs)
        for arc, cap_style in zip(arcs, m.CapStyleType, strict=True):
            label = m.Text(cap_style.name, font_size=24).next_to(arc, m.DOWN)
            self.add(label)
        self.wait()
