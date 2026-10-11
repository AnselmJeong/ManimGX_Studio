"""Walk me through rearranging a^2 + b^2 = c^2 to solve for a^2."""

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self):
        eq1 = m.MathTex(
            "{{a}}^2",
            "+",
            "{{b}}^2",
            "=",
            "{{c}}^2",
        ).scale(1.5)
        eq2 = m.MathTex(
            "{{a}}^2",
            "=",
            "{{c}}^2",
            "-",
            "{{b}}^2",
        ).scale(1.5)
        eq2.move_to(eq1)

        box = m.SurroundingRectangle(eq1, color=m.YELLOW, buff=0.2)

        self.play(m.Write(eq1), run_time=2.0)
        self.play(m.Create(box), run_time=0.8)
        self.play(m.FadeOut(box), run_time=0.5)
        self.play(m.TransformMatchingTex(eq1, eq2), run_time=2.5)
        self.wait(1.0)
        self.wait(0.5)
