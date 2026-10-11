import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex(
            "Inscribed sphere volume as fraction of cube",
        ).to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        square_2d = m.Square(
            side_length=2.5,
            color=m.WHITE,
            stroke_width=2,
        ).shift(m.LEFT * 3)
        circle_2d = m.Circle(
            radius=1.25,
            color=m.YELLOW,
            fill_color=m.YELLOW,
            fill_opacity=0.45,
        ).move_to(square_2d.get_center())
        ratio_2d = (
            m.MathTex(
                "d = 2:\\ \\frac{\\pi}{4} \\approx 0.785",
            )
            .scale(0.7)
            .next_to(square_2d, m.DOWN, buff=0.4)
        )
        self.play(m.Create(square_2d), m.Create(circle_2d), m.Write(ratio_2d))
        self.wait(0.3)

        square_3d = m.Square(
            side_length=2.5,
            color=m.WHITE,
            stroke_width=2,
        ).shift(m.RIGHT * 3)
        circle_3d = m.Circle(
            radius=1.25,
            color=m.YELLOW,
            fill_color=m.YELLOW,
            fill_opacity=0.45,
        ).move_to(square_3d.get_center())
        ratio_3d = (
            m.MathTex(
                "d = 3:\\ \\frac{\\pi}{6} \\approx 0.524",
            )
            .scale(0.7)
            .next_to(square_3d, m.DOWN, buff=0.4)
        )
        self.play(m.Create(square_3d), m.Create(circle_3d), m.Write(ratio_3d))
        self.wait(0.3)

        warning = m.Tex(
            "In high $d$, ratio $\\to 0$ — the cube has corners!",
            color=m.RED,
        ).to_edge(m.DOWN, buff=0.5)
        self.play(m.Write(warning))
        self.wait(2.0)
