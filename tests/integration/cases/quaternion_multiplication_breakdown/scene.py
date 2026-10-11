import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Quaternion product breakdown").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        q1 = m.MathTex("q_1 = a_1 + b_1 i + c_1 j + d_1 k").scale(0.9).shift(m.UP * 2.0)
        q2 = m.MathTex("q_2 = a_2 + b_2 i + c_2 j + d_2 k").scale(0.9).shift(m.UP * 1.1)
        self.play(m.Write(q1), m.Write(q2))

        result = (
            m.MathTex(
                "q_1 q_2 = ",
                "(a_1 a_2 - \\vec{v}_1 \\cdot \\vec{v}_2)",
                " + ",
                "(a_1 \\vec{v}_2 + a_2 \\vec{v}_1 + \\vec{v}_1 \\times \\vec{v}_2)",
            )
            .scale(0.7)
            .shift(m.DOWN * 0.4)
        )
        result[1].set_color(m.YELLOW)
        result[3].set_color(m.GREEN)
        self.play(m.Write(result))

        legend = (
            m.VGroup(
                m.Tex("Scalar part: dot product", color=m.YELLOW).scale(0.6),
                m.Tex("Vector part: cross product + linear", color=m.GREEN).scale(0.6),
            )
            .arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.25)
            .to_edge(m.DOWN, buff=0.6)
        )
        self.play(m.Write(legend))
        self.wait(2.0)
