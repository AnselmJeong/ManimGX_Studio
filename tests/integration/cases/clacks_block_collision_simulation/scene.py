import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Clacks: counting block collisions").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        floor = m.Line(m.LEFT * 6, m.RIGHT * 6, color=m.WHITE, stroke_width=2).shift(
            m.DOWN * 1.5
        )
        wall = m.Line(
            m.LEFT * 6 + m.DOWN * 1.5,
            m.LEFT * 6 + m.UP * 1.5,
            color=m.WHITE,
            stroke_width=3,
        )
        self.add(floor, wall)

        small = m.Square(
            side_length=0.5,
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.55,
        ).move_to([-3.0, -1.25, 0])
        big = m.Square(
            side_length=1.0,
            color=m.RED,
            fill_color=m.RED,
            fill_opacity=0.55,
        ).move_to([2.0, -1.0, 0])
        self.play(m.FadeIn(small), m.FadeIn(big))

        self.play(
            big.animate.shift(m.LEFT * 3),
            small.animate.shift(m.LEFT * 0.6),
            run_time=1.5,
        )
        self.play(small.animate.shift(m.LEFT * 1.2), run_time=0.7)
        self.play(small.animate.shift(m.RIGHT * 1.0), run_time=0.6)
        self.play(
            big.animate.shift(m.LEFT * 0.4),
            small.animate.shift(m.LEFT * 0.3),
            run_time=0.7,
        )
        self.play(big.animate.shift(m.RIGHT * 3.5), run_time=1.8)

        count = (
            m.MathTex(
                "\\text{Collisions} \\to 3,\\ 31,\\ 314,\\ 3141, \\ldots",
            )
            .scale(0.75)
            .to_edge(m.DOWN, buff=0.55)
        )
        self.play(m.Write(count))
        self.wait(2.0)
