# Source: manim/animation/rotation.py
from typing import TypedDict

import manimgx as m


class PlayKeywords(TypedDict):
    run_time: float


class RotatingDifferentAxis(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        cube = m.Cube()
        arrow2d = m.Arrow(start=[0, -1.2, 1], end=[0, 1.2, 1], color=m.YELLOW_E)
        cube_group = m.VGroup(cube, arrow2d)
        self.set_camera_orientation(gamma=0, phi=40 * m.DEGREES, theta=40 * m.DEGREES)
        self.add(axes, cube_group)
        play_kw: PlayKeywords = {"run_time": 1.5}
        self.play(m.Rotating(cube_group, m.PI), **play_kw)
        self.play(m.Rotating(cube_group, m.PI, axis=m.UP), **play_kw)
        self.play(m.Rotating(cube_group, 180 * m.DEGREES, axis=m.RIGHT), **play_kw)
        self.wait(0.5)
