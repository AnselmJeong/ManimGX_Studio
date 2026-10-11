import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Conservation of momentum").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        before_title = m.Tex("Before").scale(0.65).shift(m.LEFT * 2 + m.UP * 1.7)
        block1 = m.Rectangle(
            width=0.7,
            height=0.7,
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.55,
        ).move_to([-3.5, 0.5, 0])
        block2 = m.Rectangle(
            width=1.2,
            height=1.0,
            color=m.RED,
            fill_color=m.RED,
            fill_opacity=0.55,
        ).move_to([-1.5, 0.5, 0])
        arr1_b = m.Arrow([-3.5, 0.5, 0], [-2.7, 0.5, 0], color=m.YELLOW, buff=0)
        arr2_b = m.Arrow([-1.5, 0.5, 0], [-2.1, 0.5, 0], color=m.YELLOW, buff=0)

        after_title = m.Tex("After").scale(0.65).shift(m.RIGHT * 2.5 + m.UP * 1.7)
        block1a = block1.copy().move_to([1.5, 0.5, 0])
        block2a = block2.copy().move_to([3.5, 0.5, 0])
        arr1_a = m.Arrow([1.5, 0.5, 0], [1.0, 0.5, 0], color=m.YELLOW, buff=0)
        arr2_a = m.Arrow([3.5, 0.5, 0], [4.3, 0.5, 0], color=m.YELLOW, buff=0)

        self.play(m.Write(before_title), m.FadeIn(block1), m.FadeIn(block2))
        self.play(m.GrowArrow(arr1_b), m.GrowArrow(arr2_b))
        self.play(m.Write(after_title), m.FadeIn(block1a), m.FadeIn(block2a))
        self.play(m.GrowArrow(arr1_a), m.GrowArrow(arr2_a))

        eq = m.MathTex(
            "p_1 + p_2 = p_1' + p_2'",
            color=m.YELLOW,
        ).to_edge(m.DOWN, buff=0.6)
        self.play(m.Write(eq))
        self.wait(2.0)
