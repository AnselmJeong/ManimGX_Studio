import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Weighted coin: $P(\\text{heads}) = 0.7$")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        coin = m.Circle(
            radius=1.5,
            color=m.YELLOW,
            fill_color=m.YELLOW,
            fill_opacity=0.35,
            stroke_width=3,
        ).shift(m.LEFT * 3.5)
        h_label = m.Tex("H", color=m.YELLOW).scale(1.6).move_to(coin.get_center())
        self.play(m.Create(coin), m.Write(h_label))

        bar_h = m.Rectangle(
            width=0.7 * 5,
            height=0.6,
            color=m.YELLOW,
            fill_color=m.YELLOW,
            fill_opacity=0.6,
        ).move_to([1.25, 0.5, 0])
        bar_t = m.Rectangle(
            width=0.3 * 5,
            height=0.6,
            color=m.GREY,
            fill_color=m.GREY,
            fill_opacity=0.6,
        ).move_to([4.25, 0.5, 0])
        h_text = (
            m.MathTex("P(H) = 0.7", color=m.YELLOW)
            .scale(0.6)
            .next_to(bar_h, m.DOWN, buff=0.1)
        )
        t_text = (
            m.MathTex("P(T) = 0.3", color=m.GREY)
            .scale(0.6)
            .next_to(bar_t, m.DOWN, buff=0.1)
        )
        self.play(m.Create(bar_h), m.Create(bar_t))
        self.play(m.Write(h_text), m.Write(t_text))
        self.wait(2.0)
