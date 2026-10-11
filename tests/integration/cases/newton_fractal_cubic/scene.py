import cmath
import math

import numpy as np

import manimgx as m


def newton_basin_cubic(width: int, height: int) -> np.ndarray:
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    roots = [cmath.exp(2j * math.pi * k / 3) for k in range(3)]
    palette = [(240, 100, 100), (100, 220, 100), (100, 140, 240)]
    for j in range(height):
        for i in range(width):
            x = -1.6 + 3.2 * (i + 0.5) / width
            y = -1.2 + 2.4 * (j + 0.5) / height
            z = complex(x, y)
            for k in range(25):
                d = 3 * z * z
                if abs(d) < 1e-8:
                    break
                z = z - (z * z * z - 1) / d
            best = 0
            best_d = abs(z - roots[0])
            for ri in range(1, 3):
                d = abs(z - roots[ri])
                if d < best_d:
                    best_d = d
                    best = ri
            r, g, b = palette[best]
            arr[height - 1 - j, i] = (r, g, b, 255)
    return arr


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Newton fractal: $z^3 - 1$").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        arr = newton_basin_cubic(180, 135)
        img = m.ImageMobject(arr)
        img.stretch_to_fit_height(4.0).stretch_to_fit_width(5.3).move_to(m.DOWN * 0.4)
        self.play(m.FadeIn(img), run_time=1.5)

        note = (
            m.MathTex(
                "\\text{three roots of unity, fractal basin boundary}", color=m.YELLOW
            )
            .scale(0.7)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(note))
        self.wait(2.0)
