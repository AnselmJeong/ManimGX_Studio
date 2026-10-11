"""Walk me through deriving the quadratic formula step by step from a*x^2 + b*x + c = 0."""

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        # Each equation is a single LaTeX string with {{...}} markers around
        # the symbols we want TransformMatchingTex to pair across steps.
        # Splitting LaTeX structures like \frac{...}{...} across multiple
        # MathTex args breaks Typst compilation; keep them whole.
        eq1 = m.MathTex(R"{{a}} {{x^2}} + {{b}} {{x}} + {{c}} = 0").scale(1.2)
        eq2 = m.MathTex(R"{{a}} {{x^2}} + {{b}} {{x}} = - {{c}}").scale(1.2)
        eq3 = m.MathTex(
            R"{{x^2}} + \frac{ {{b}} }{ {{a}} } {{x}} = - \frac{ {{c}} }{ {{a}} }"
        ).scale(1.2)
        eq4 = m.MathTex(
            R"{{x}} = \frac{ - {{b}} \pm \sqrt{ {{b}}^2 - 4 {{a}} {{c}} } }{ 2 {{a}} }"
        ).scale(1.2)

        # Keep everything centered at the same point so the morphs read as
        # "rewrite in place."
        for eq in (eq2, eq3, eq4):
            eq.move_to(eq1)

        self.play(m.Write(eq1), run_time=2.0)
        self.wait(0.7)

        self.play(
            m.TransformMatchingTex(eq1, eq2, path_arc=-90 * m.DEGREES),
            run_time=2.5,
        )
        self.wait(0.6)

        self.play(
            m.TransformMatchingTex(eq2, eq3, path_arc=-90 * m.DEGREES),
            run_time=2.5,
        )
        self.wait(0.6)

        self.play(
            m.TransformMatchingTex(eq3, eq4, path_arc=-90 * m.DEGREES),
            run_time=2.5,
        )
        self.wait(0.5)
