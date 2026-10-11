import numpy as np

import manimgx as m


def sierpinski(
    p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, depth: int
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    if depth == 0:
        return [(p1, p2, p3)]
    m12 = (p1 + p2) / 2
    m23 = (p2 + p3) / 2
    m31 = (p3 + p1) / 2
    return (
        sierpinski(p1, m12, m31, depth - 1)
        + sierpinski(m12, p2, m23, depth - 1)
        + sierpinski(m31, m23, p3, depth - 1)
    )


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Sierpinski triangle, depths 0–5").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        SIZE = 2.6
        p1 = np.array([0.0, SIZE, 0.0])
        p2 = np.array([-SIZE * np.sqrt(3) / 2, -SIZE / 2, 0.0])
        p3 = np.array([SIZE * np.sqrt(3) / 2, -SIZE / 2, 0.0])

        current = None
        label = None
        for depth in range(6):
            triangles = sierpinski(p1, p2, p3, depth)
            grp = m.VGroup(
                *[
                    m.Polygon(
                        *t,
                        color=m.YELLOW,
                        fill_color=m.YELLOW,
                        fill_opacity=0.45,
                        stroke_width=max(0.3, 1.8 - depth * 0.3),
                    )
                    for t in triangles
                ]
            )
            new_label = m.MathTex(f"\\text{{depth }} {depth}").to_corner(m.UR, buff=0.5)

            if current is None or label is None:
                current, label = grp, new_label
                self.play(m.Create(current), m.Write(label))
            else:
                self.play(
                    m.Transform(current, grp),
                    m.Transform(label, new_label),
                    run_time=1.2,
                )
            self.wait(0.4)
        self.wait(1.4)
