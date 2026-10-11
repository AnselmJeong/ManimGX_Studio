import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        eq1 = m.MathTex("V", "-", "E", "+", "F", "=", "2").scale(1.3)
        self.play(m.Write(eq1))
        self.wait(0.7)

        eq2 = m.MathTex("F", "=", "E", "-", "V", "+", "2").scale(1.3)
        self.play(m.TransformMatchingTex(eq1, eq2))
        self.wait(0.7)

        eq3 = m.MathTex(
            "F",
            "=",
            "E",
            "-",
            "n",
            "-",
            "\\binom{n}{4}",
            "+",
            "2",
        ).scale(1.25)
        self.play(m.TransformMatchingTex(eq2, eq3))
        sub_label_v = (
            m.Tex(
                "$V = n + \\binom{n}{4}$",
                color=m.GREY,
            )
            .scale(0.7)
            .next_to(eq3, m.DOWN, buff=0.6)
        )
        self.play(m.FadeIn(sub_label_v))
        self.wait(0.9)
        self.play(m.FadeOut(sub_label_v))

        eq4 = m.MathTex(
            "F",
            "=",
            "\\binom{n}{2}",
            "+",
            "2\\binom{n}{4}",
            "+",
            "n",
            "-",
            "n",
            "-",
            "\\binom{n}{4}",
            "+",
            "2",
        ).scale(1.0)
        self.play(m.TransformMatchingTex(eq3, eq4))
        sub_label_e = (
            m.Tex(
                "$E = \\binom{n}{2} + 2\\binom{n}{4} + n$",
                color=m.GREY,
            )
            .scale(0.7)
            .next_to(eq4, m.DOWN, buff=0.6)
        )
        self.play(m.FadeIn(sub_label_e))
        self.wait(1.0)
        self.play(m.FadeOut(sub_label_e))

        eq5 = m.MathTex(
            "F",
            "=",
            "\\binom{n}{2}",
            "+",
            "\\binom{n}{4}",
            "+",
            "2",
        ).scale(1.3)
        self.play(m.TransformMatchingTex(eq4, eq5))
        self.wait(0.7)

        eq6 = (
            m.MathTex(
                "F",
                "=",
                "2",
                "+",
                "\\binom{n}{2}",
                "+",
                "\\binom{n}{4}",
            )
            .scale(1.4)
            .set_color(m.YELLOW)
        )
        self.play(m.TransformMatchingTex(eq5, eq6))

        caption = (
            m.Tex(
                "Moser's formula",
                color=m.YELLOW,
            )
            .scale(0.9)
            .next_to(eq6, m.DOWN, buff=0.6)
        )
        self.play(m.Write(caption))
        self.wait(2.0)
