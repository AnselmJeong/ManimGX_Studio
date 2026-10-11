import math

import numpy as np

import manimgx as m

HUE_COLORS = [
    "#E03030",
    "#E0A030",
    "#E0E030",
    "#30E030",
    "#30E0E0",
    "#3030E0",
    "#A030E0",
    "#E030C0",
]


def color_for(z: complex) -> str:
    w = z * z
    angle = math.atan2(w.imag, w.real)
    idx = int(((angle / (2 * math.pi)) + 0.5) * len(HUE_COLORS)) % len(HUE_COLORS)
    return HUE_COLORS[idx]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Domain coloring of ", "$f(z) = z^2$")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        cells = m.VGroup()
        for x in np.arange(-2.4, 2.41, 0.32):
            for y in np.arange(-2.4, 2.41, 0.32):
                color = color_for(complex(x, y))
                cells.add(
                    m.Square(
                        side_length=0.3,
                        color=color,
                        fill_color=color,
                        fill_opacity=0.9,
                        stroke_width=0,
                    ).move_to([x, y, 0]),
                )
        self.play(m.FadeIn(cells), run_time=2.0)
        self.wait(2.0)
