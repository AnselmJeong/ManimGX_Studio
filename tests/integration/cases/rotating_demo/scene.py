# Source: manim/animation/rotation.py
from typing import TypedDict

import manimgx as m
from manimgx.typing import Point3D


class RotationKeywords(TypedDict):
    about_point: Point3D
    run_time: float


class RotatingDemo(m.Scene):
    def construct(self):
        circle = m.Circle(radius=1, color=m.BLUE)
        line = m.Line(start=m.ORIGIN, end=m.RIGHT)
        arrow = m.Arrow(start=m.ORIGIN, end=m.RIGHT, buff=0, color=m.GOLD)
        vg = m.VGroup(circle, line, arrow)
        self.add(vg)
        anim_kw: RotationKeywords = {
            "about_point": arrow.get_start(),
            "run_time": 1,
        }
        self.play(m.Rotating(arrow, 180 * m.DEGREES, **anim_kw))
        self.play(m.Rotating(arrow, m.PI, **anim_kw))
        self.play(m.Rotating(vg, m.PI, about_point=m.RIGHT))
        self.play(m.Rotating(vg, m.PI, axis=m.UP, about_point=m.ORIGIN))
        self.play(m.Rotating(vg, m.PI, axis=m.RIGHT, about_edge=m.UP))
        self.play(vg.animate.move_to(m.ORIGIN))
