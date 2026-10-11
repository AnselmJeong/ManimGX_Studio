import numpy as np

import manimgx as m

TRIANGLES = [
    ([(0.0, 0.0), (1.0, 0.0), (0.5, 0.87)], "equilateral", (0.5, 0.87)),
    ([(0.0, 0.0), (1.0, 0.0), (0.25, 0.8)], "acute", (0.25, 0.8)),
    ([(0.0, 0.0), (1.0, 0.0), (0.5, 0.3)], "obtuse", (0.5, 0.3)),
]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Triangles up to similarity $\\to$ a single point",
            )
            .scale(0.75)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        for i, (verts, name, _) in enumerate(TRIANGLES):
            tri = m.Polygon(
                *[np.array([v[0], v[1], 0]) for v in verts],
                color=m.YELLOW,
                fill_color=m.YELLOW,
                fill_opacity=0.35,
                stroke_width=2,
            )
            tri.scale(0.8).move_to([-4.5, 2.2 - i * 2, 0])
            label = m.Tex(name).scale(0.5).next_to(tri, m.DOWN, buff=0.12)
            self.play(m.FadeIn(tri), m.Write(label), run_time=0.4)

        plane = m.NumberPlane(
            x_range=[-1, 2, 1],
            y_range=[-1, 2, 1],
            x_length=5,
            y_length=5,
        ).shift(m.RIGHT * 3)
        self.play(m.Create(plane))

        for _, _, (mx, my) in TRIANGLES:
            self.play(
                m.FadeIn(
                    m.Dot(plane.coords_to_point(mx, my), color=m.RED, radius=0.11)
                ),
                run_time=0.3,
            )

        caption = (
            m.Tex(
                "Each triangle = one point in moduli space",
            )
            .scale(0.65)
            .to_edge(m.DOWN, buff=0.5)
        )
        self.play(m.Write(caption))
        self.wait(2.0)
