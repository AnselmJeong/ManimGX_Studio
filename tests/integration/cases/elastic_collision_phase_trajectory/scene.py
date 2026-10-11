import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex(
            "Elastic collision: velocities exchange",
        ).to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        plane = m.NumberPlane(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=8,
            y_length=8,
        )
        self.add(plane)

        before = plane.coords_to_point(2, -1)
        after = plane.coords_to_point(-1, 2)
        before_dot = m.Dot(before, color=m.YELLOW, radius=0.12)
        after_dot = m.Dot(after, color=m.GREEN, radius=0.12)
        before_label = (
            m.Tex("before", color=m.YELLOW)
            .scale(0.6)
            .next_to(before_dot, m.UR, buff=0.1)
        )
        after_label = (
            m.Tex("after", color=m.GREEN).scale(0.6).next_to(after_dot, m.UR, buff=0.1)
        )
        arrow = m.Arrow(before, after, color=m.RED, buff=0.15, stroke_width=4)

        self.play(m.FadeIn(before_dot), m.Write(before_label))
        self.play(m.GrowArrow(arrow))
        self.play(m.FadeIn(after_dot), m.Write(after_label))

        conserve = (
            m.MathTex(
                "v_1 + v_2 = 1",
                "\\quad",
                "v_1^2 + v_2^2 = 5",
            )
            .scale(0.85)
            .to_edge(m.DOWN, buff=0.5)
        )
        self.play(m.Write(conserve))
        self.wait(2.0)
