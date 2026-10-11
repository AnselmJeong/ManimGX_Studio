import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Richard Hamming, Bell Labs, 1947").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        year = m.Tex("1947", color=m.YELLOW).scale(2.5).move_to(m.UP * 0.5)
        self.play(m.Write(year))

        quote = (
            m.Tex(
                "Detect an error? Locate it. Correct it.",
            )
            .scale(0.7)
            .move_to(m.DOWN * 1.7)
        )
        self.play(m.Write(quote))
        self.wait(2.0)
