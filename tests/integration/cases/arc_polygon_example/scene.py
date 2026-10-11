# Source: manim/mobject/geometry/arc.py
from typing import TypedDict

import numpy as np

import manimgx as m


class _ArcConf(TypedDict, total=False):
    stroke_width: float


class _PolyConf(TypedDict, total=False):
    stroke_width: float
    stroke_color: object
    fill_opacity: float
    color: object


class ArcPolygonExample(m.Scene):
    def construct(self):
        arc_conf: _ArcConf = {"stroke_width": 0}
        stroke_color = m.BLUE
        color = m.PURPLE
        poly_conf: _PolyConf = {
            "stroke_width": 10,
            "stroke_color": stroke_color,
            "fill_opacity": 1,
            "color": color,
        }
        a = (-1.0, 0.0, 0.0)
        b = (1.0, 0.0, 0.0)
        c = (0.0, float(np.sqrt(3)), 0.0)
        arc0 = m.ArcBetweenPoints(a, b, radius=2, **arc_conf)
        arc1 = m.ArcBetweenPoints(b, c, radius=2, **arc_conf)
        arc2 = m.ArcBetweenPoints(c, a, radius=2, **arc_conf)
        reuleaux_tri = m.ArcPolygonFromArcs(
            arc0,
            arc1,
            arc2,
            stroke_width=poly_conf["stroke_width"],
            stroke_color=stroke_color,
            fill_opacity=poly_conf["fill_opacity"],
            color=color,
        )
        self.play(m.FadeIn(reuleaux_tri))
        self.wait(2)
