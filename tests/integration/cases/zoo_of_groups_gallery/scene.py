import manimgx as m

GROUPS = [
    ("C_2", 2, m.BLUE),
    ("C_4", 4, m.GREEN),
    ("D_6", 6, m.YELLOW),
    ("S_3", 3, m.RED),
    ("D_8", 8, m.PURPLE),
    ("D_{12}", 12, m.ORANGE),
]
POSITIONS = [(-4, 1.5), (0, 1.5), (4, 1.5), (-4, -1.5), (0, -1.5), (4, -1.5)]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Zoo of groups").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        for (name, n, color), (px, py) in zip(GROUPS, POSITIONS):
            shape = m.RegularPolygon(n=n, color=color, stroke_width=2.5).scale(0.55)
            shape.move_to([px, py, 0])
            label = m.MathTex(name).scale(0.75).next_to(shape, m.DOWN, buff=0.2)
            self.play(m.FadeIn(shape), m.Write(label), run_time=0.4)
        self.wait(2.0)
