import manimgx as m


def _d2xy(n: int, d: int) -> tuple[int, int]:
    x = y = 0
    t = d
    s = 1
    while s < n:
        rx = (t // 2) & 1
        ry = (t ^ rx) & 1
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


def hilbert_points(order: int, size: float = 5.0) -> list[tuple[float, float]]:
    n = 2**order
    raw = [_d2xy(n, i) for i in range(n * n)]
    return [
        (x / (n - 1) * size - size / 2, y / (n - 1) * size - size / 2) for x, y in raw
    ]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Hilbert curve, orders 1–5").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        curve = None
        label = None
        for order in range(1, 6):
            pts = hilbert_points(order, size=5.0)
            new_curve = m.VMobject(stroke_color=m.YELLOW, stroke_width=4.0 / order)
            new_curve.set_points_as_corners([(x, y, 0) for x, y in pts])
            new_label = m.MathTex(f"\\text{{order }} {order}").to_corner(m.UR, buff=0.5)

            if curve is None or label is None:
                curve = new_curve
                label = new_label
                self.play(m.Create(curve), m.Write(label))
            else:
                self.play(
                    m.Transform(curve, new_curve),
                    m.Transform(label, new_label),
                    run_time=1.5,
                )
            self.wait(0.6)
        self.wait(1.5)
