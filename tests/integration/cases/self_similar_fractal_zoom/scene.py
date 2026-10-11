import numpy as np

import manimgx as m


def cantor_segments(
    start: np.ndarray, end: np.ndarray, depth: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    if depth == 0:
        return [(start, end)]
    diff = end - start
    a1 = start
    b1 = start + diff / 3
    a2 = start + 2 * diff / 3
    b2 = end
    return cantor_segments(a1, b1, depth - 1) + cantor_segments(a2, b2, depth - 1)


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex(
            "Cantor set: remove the middle third, recurse",
        ).to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        start = np.array([-5.5, 0.0, 0.0])
        end = np.array([5.5, 0.0, 0.0])

        for depth in range(7):
            y = 2.2 - depth * 0.55
            offset = np.array([0.0, y, 0.0])
            segs = cantor_segments(start, end, depth)
            lines = m.VGroup(
                *[
                    m.Line(
                        s + offset,
                        e + offset,
                        color=m.YELLOW,
                        stroke_width=4,
                    )
                    for s, e in segs
                ]
            )
            self.play(m.Create(lines, lag_ratio=0.01), run_time=0.5)
            self.wait(0.18)
        self.wait(1.4)
