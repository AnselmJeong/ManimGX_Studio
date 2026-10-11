"""Show what f(z) = z^2 does to the plane. Map a small grid through it."""

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        in_plane = (
            m.ComplexPlane(
                x_range=(-2.0, 2.0, 1.0),
                y_range=(-2.0, 2.0, 1.0),
            )
            .scale(0.5)
            .move_to(3.5 * m.LEFT)
        )

        out_plane = (
            m.ComplexPlane(
                x_range=(-3.0, 3.0, 1.0),
                y_range=(-3.0, 3.0, 1.0),
            )
            .scale(0.5)
            .move_to(3.5 * m.RIGHT)
        )

        grid = m.VGroup(
            *[
                m.Square(side_length=0.3).move_to(in_plane.n2p(complex(x, y)))
                for x in (0.3, 0.6, 0.9)
                for y in (0.3, 0.6, 0.9)
            ]
        ).set_stroke(m.YELLOW, 2.0)

        label = m.MathTex(R"z \mapsto z^2").scale(1.0).move_to(m.ORIGIN + 0.2 * m.UP)

        self.play(
            m.Create(in_plane),
            m.Create(out_plane),
            run_time=1.5,
        )
        self.play(m.Write(label), run_time=0.6)
        self.play(m.FadeIn(grid), run_time=0.8)
        self.play(
            m.ApplyPointwiseFunction(
                lambda p: out_plane.n2p(in_plane.p2n(p) ** 2),
                grid,
            ),
            run_time=3.0,
        )
        self.wait(1.0)
        self.wait(0.5)
