import numpy as np

import manimgx as m


def mandelbrot_pixels(
    width: int,
    height: int,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    max_iter: int = 30,
) -> np.ndarray:
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    for j in range(height):
        for i in range(width):
            cx = x0 + (i + 0.5) * (x1 - x0) / width
            cy = y0 + (j + 0.5) * (y1 - y0) / height
            c = complex(cx, cy)
            z = 0j
            n = 0
            while abs(z) < 2 and n < max_iter:
                z = z * z + c
                n += 1
            t = n / max_iter
            if n >= max_iter:
                r, g, b = 0, 0, 0
            else:
                r = int(255 * t)
                g = int(180 * (1 - t))
                b = int(220 * (0.5 + 0.5 * np.sin(6 * t)))
            arr[height - 1 - j, i] = (r, g, b, 255)
    return arr


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Mandelbrot set: parameter space").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        arr = mandelbrot_pixels(160, 120, -2.2, 1.0, -1.2, 1.2, max_iter=24)
        img = m.ImageMobject(arr)
        img.stretch_to_fit_height(3.5).stretch_to_fit_width(4.7).move_to(
            m.ORIGIN + m.DOWN * 0.4
        )
        self.play(m.FadeIn(img), run_time=1.5)

        caption = (
            m.MathTex(
                "c \\in \\mathbb C\\;:\\;\\{0, c, c^2+c, \\ldots\\}\\text{ stays"
                " bounded}",
                color=m.YELLOW,
            )
            .scale(0.7)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(caption))
        self.wait(2.0)
