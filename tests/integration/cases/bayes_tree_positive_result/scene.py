import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Bayes' tree: positive test result")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        top = m.Tex("All people").scale(0.75).move_to([0, 2.2, 0])
        sick = m.Tex("Sick (1\\%)", color=m.RED).scale(0.65).move_to([-3.0, 0.5, 0])
        healthy = (
            m.Tex("Healthy (99\\%)", color=m.GREEN).scale(0.65).move_to([3.0, 0.5, 0])
        )

        sick_pos = (
            m.MathTex(
                "P(+|\\text{S}) \\cdot 0.01",
                color=m.YELLOW,
            )
            .scale(0.55)
            .move_to([-4.0, -1.6, 0])
        )
        sick_neg = (
            m.MathTex(
                "P(-|\\text{S}) \\cdot 0.01",
            )
            .scale(0.55)
            .move_to([-1.8, -1.6, 0])
        )
        healthy_pos = (
            m.MathTex(
                "P(+|\\text{H}) \\cdot 0.99",
                color=m.YELLOW,
            )
            .scale(0.55)
            .move_to([2.0, -1.6, 0])
        )
        healthy_neg = (
            m.MathTex(
                "P(-|\\text{H}) \\cdot 0.99",
            )
            .scale(0.55)
            .move_to([4.2, -1.6, 0])
        )

        self.play(m.Write(top))
        self.play(m.Write(sick), m.Write(healthy))
        self.play(
            m.Write(sick_pos),
            m.Write(sick_neg),
            m.Write(healthy_pos),
            m.Write(healthy_neg),
        )

        lines = m.VGroup(
            m.Line(top.get_bottom(), sick.get_top(), color=m.WHITE),
            m.Line(top.get_bottom(), healthy.get_top(), color=m.WHITE),
            m.Line(sick.get_bottom(), sick_pos.get_top(), color=m.WHITE),
            m.Line(sick.get_bottom(), sick_neg.get_top(), color=m.WHITE),
            m.Line(healthy.get_bottom(), healthy_pos.get_top(), color=m.WHITE),
            m.Line(healthy.get_bottom(), healthy_neg.get_top(), color=m.WHITE),
        )
        self.play(m.Create(lines))
        self.wait(2.0)
