import manimgx as m

NUM_CIRCLES = 8


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Concentric circles expanding").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        anims: list[m.Animation] = []
        for k in range(NUM_CIRCLES):
            target_r = 0.35 + k * 0.4
            circle = m.Circle(radius=target_r, color=m.BLUE, stroke_width=2.5)
            anims.append(m.GrowFromCenter(circle))
        self.play(m.LaggedStart(*anims, lag_ratio=0.15), run_time=3.0)
        self.wait(1.5)
