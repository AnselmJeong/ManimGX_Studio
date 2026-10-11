# Source: manim/mobject/geometry/arc.py
from typing import TypedDict

import numpy as np

import manimgx as m


class _ArcConf(TypedDict, total=False):
    stroke_width: float
    stroke_color: object
    fill_opacity: float
    color: object


class _PolyConf(TypedDict, total=False):
    color: object


class ArcPolygonExample2(m.Scene):
    def construct(self):
        stroke_color = m.BLUE
        color = m.GREEN
        arc_conf: _ArcConf = {
            "stroke_width": 3,
            "stroke_color": stroke_color,
            "fill_opacity": 0.5,
            "color": color,
        }
        poly_color = None
        _poly_conf: _PolyConf = {"color": poly_color}
        a = (-1.0, 0.0, 0.0)
        b = (1.0, 0.0, 0.0)
        c = (0.0, float(np.sqrt(3)), 0.0)
        arc0 = m.ArcBetweenPoints(
            a,
            b,
            radius=2,
            stroke_width=arc_conf["stroke_width"],
            stroke_color=stroke_color,
            fill_opacity=arc_conf["fill_opacity"],
            color=color,
        )
        arc1 = m.ArcBetweenPoints(
            b,
            c,
            radius=2,
            stroke_width=arc_conf["stroke_width"],
            stroke_color=stroke_color,
            fill_opacity=arc_conf["fill_opacity"],
            color=color,
        )
        arc2 = m.ArcBetweenPoints(c, a, radius=2, stroke_color=m.RED)
        reuleaux_tri = m.ArcPolygonFromArcs(arc0, arc1, arc2, color=poly_color)
        self.play(m.FadeIn(reuleaux_tri))
        self.wait(2)
