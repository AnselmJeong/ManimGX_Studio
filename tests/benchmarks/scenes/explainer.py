"""A classic explainer: a curve drawn on axes, its area and its integral, then a tangent
line sliding along it."""

import numpy as np

import manimgx as m


class Explainer(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[0, 2 * np.pi, np.pi / 2], y_range=[-1.5, 1.5, 1])
        sine = axes.plot(np.sin, color=m.BLUE, stroke_width=6)
        dot = m.Dot(axes.i2gp(0, sine), radius=0.12, color=m.YELLOW)
        area = axes.get_area(sine, x_range=(0, np.pi), color=m.BLUE, opacity=0.4)
        label = m.MathTex(r"y = \sin x", font_size=72).to_corner(m.UR)
        integral = m.MathTex(r"\int_0^\pi \sin x \, dx = 2", font_size=72).to_corner(
            m.UR
        )
        self.play(m.Create(axes), m.Write(label))
        self.play(m.Create(sine), m.MoveAlongPath(dot, sine), run_time=2.5)
        self.play(m.FadeIn(area), m.TransformMatchingTex(label, integral))
        along = m.ValueTracker(0)
        tangent = m.always_redraw(
            lambda: m.TangentLine(
                sine, alpha=along.get_value(), length=3, color=m.YELLOW
            )
        )
        dot.add_updater(
            lambda d: d.move_to(sine.point_from_proportion(along.get_value()))
        )
        self.add(tangent, dot)
        self.play(along.animate.set_value(1), run_time=4)
        self.wait()
