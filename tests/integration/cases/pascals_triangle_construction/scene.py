import math

import manimgx as m

ROWS = 6
SPACING_X = 0.65
SPACING_Y = 0.65


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Pascal's triangle: each entry = sum of two above",
            )
            .scale(0.8)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        cells: list[list[m.Integer]] = []
        for row in range(ROWS + 1):
            y = 2.4 - row * SPACING_Y
            row_cells = []
            for k in range(row + 1):
                x = (k - row / 2.0) * SPACING_X
                row_cells.append(
                    m.Integer(math.comb(row, k)).scale(0.75).move_to([x, y, 0]),
                )
            cells.append(row_cells)

        self.play(m.Write(cells[0][0]))

        for row in range(1, ROWS + 1):
            anims: list[m.Animation] = []
            for k in range(row + 1):
                target = cells[row][k]
                if k == 0 or k == row:
                    anims.append(m.Write(target))
                else:
                    left = cells[row - 1][k - 1].copy()
                    right = cells[row - 1][k].copy()
                    anims.append(m.Transform(left, target))
                    anims.append(m.Transform(right, target))
            self.play(*anims, run_time=0.6)
            self.wait(0.2)
        self.wait(1.5)
