import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Triple redundancy: $0 \\to 000$, $1 \\to 111$")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        bit = m.MathTex("1", color=m.YELLOW).scale(1.5).shift(m.LEFT * 5 + m.UP)
        encoded = (
            m.MathTex("1 1 1", color=m.YELLOW).scale(1.3).shift(m.LEFT * 1.8 + m.UP)
        )
        received = (
            m.MathTex("1 0 1", color=m.RED).scale(1.3).shift(m.RIGHT * 1.5 + m.UP)
        )
        decoded = m.MathTex("1", color=m.GREEN).scale(1.5).shift(m.RIGHT * 4.5 + m.UP)

        self.play(m.Write(bit))
        self.play(m.Write(encoded))
        self.play(m.Write(received))
        self.play(m.Write(decoded))

        arr1 = m.Arrow(bit.get_right(), encoded.get_left(), buff=0.2)
        arr2 = m.Arrow(encoded.get_right(), received.get_left(), buff=0.2, color=m.RED)
        arr3 = m.Arrow(received.get_right(), decoded.get_left(), buff=0.2)
        self.play(m.GrowArrow(arr1), m.GrowArrow(arr2), m.GrowArrow(arr3))

        labels = m.VGroup(
            m.Tex("encode").scale(0.5).next_to(arr1, m.DOWN, buff=0.1),
            m.Tex("channel", color=m.RED).scale(0.5).next_to(arr2, m.DOWN, buff=0.1),
            m.Tex("majority", color=m.GREEN).scale(0.5).next_to(arr3, m.DOWN, buff=0.1),
        )
        self.play(m.Write(labels))
        self.wait(2.0)
