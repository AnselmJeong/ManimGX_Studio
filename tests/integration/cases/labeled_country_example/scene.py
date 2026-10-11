# Source: manim/mobject/geometry/labeled.py
# CE's example downloads nation-10m.json (us-atlas 3.0.1, ISC: see nation-10m.json.LICENSE);
# it is kept beside the scene so the scene renders without the network.
import json
from pathlib import Path

import numpy as np

import manimgx as m


class LabeledCountryExample(m.Scene):
    def construct(self):
        # Fetch JSON data and process arcs
        data = json.loads(Path(__file__).with_name("nation-10m.json").read_text())
        arcs, transform = data["arcs"], data["transform"]
        sarcs: list[np.ndarray] = [
            np.cumsum(arc, axis=0) * transform["scale"] + transform["translate"]
            for arc in arcs
        ]
        sarcs.sort(key=len, reverse=True)
        ssarcs: list[np.ndarray] = sarcs[:1]

        # Compute Bounding Box
        points = np.concatenate(ssarcs)
        mins, maxs = np.min(points, axis=0), np.max(points, axis=0)

        # Build Axes
        ax = m.Axes(
            x_range=[mins[0], maxs[0], maxs[0] - mins[0]],
            x_length=10,
            y_range=[mins[1], maxs[1], maxs[1] - mins[1]],
            y_length=7,
            tips=False,
        )

        # Adjust Coordinates
        array = [[ax.c2p(*point) for point in sarc] for sarc in ssarcs]

        # Add Polygram
        polygram = m.LabeledPolygram(
            *array,
            label=m.Text("USA", font="sans-serif"),
            precision=0.01,
            fill_color=m.BLUE,
            stroke_width=0,
            fill_opacity=0.75,
        )

        # Display Circle (for reference)
        circle = m.Circle(radius=polygram.radius, color=m.WHITE).move_to(polygram.pole)

        self.add(ax)
        self.add(polygram)
        self.add(circle)
        self.wait()
