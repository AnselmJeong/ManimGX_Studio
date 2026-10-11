import math

import numpy as np

import manimgx as m

R = 2.0
N_SEGMENTS = 24


def pie_slice(start_angle: float, angle_extent: float, color: str) -> m.Polygon:
    points = [np.array([0.0, 0.0, 0.0])]
    for k in range(N_SEGMENTS + 1):
        t = k / N_SEGMENTS
        a = start_angle + t * angle_extent
        points.append(R * np.array([math.cos(a), math.sin(a), 0.0]))
    return m.Polygon(
        *points,
        color=color,
        fill_color=color,
        fill_opacity=0.75,
        stroke_width=2,
    )


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Complex rotation mixes / unmixes regions",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        colors = [m.RED, m.YELLOW, m.GREEN, m.BLUE]
        quadrants = m.VGroup(
            *[pie_slice(i * math.pi / 2, math.pi / 2, colors[i]) for i in range(4)]
        )
        self.play(m.Create(quadrants))
        self.wait(0.4)

        self.play(quadrants.animate.rotate(math.pi / 4), run_time=2.0)
        self.play(quadrants.animate.rotate(-math.pi / 4), run_time=2.0)
        self.wait(1.5)
