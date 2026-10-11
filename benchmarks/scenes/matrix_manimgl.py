import types

import manimlib

m = types.SimpleNamespace(**vars(manimlib))
m.MathTex = manimlib.Tex
m.Tex = manimlib.TexText


class TeacherScene(m.Scene):
    def construct(self) -> None:
        matrix = m.Matrix([[1, 2], [3, 1]]).scale(1.0)
        vec = m.Matrix([[2], [1]]).scale(1.0)
        equals = m.MathTex("=").scale(1.2)
        _line = (
            m.VGroup(matrix, vec, equals).arrange(m.RIGHT, buff=0.3).shift(m.UP * 0.6)
        )

        self.play(m.Write(matrix), m.Write(vec), m.Write(equals))
        self.wait(0.4)

        step = (
            m.Matrix(
                [["1 \\cdot 2 + 2 \\cdot 1"], ["3 \\cdot 2 + 1 \\cdot 1"]],
                h_buff=2.4,
            )
            .scale(0.85)
            .next_to(equals, m.RIGHT, buff=0.3)
        )
        self.play(m.Write(step))
        self.wait(0.8)

        result = m.Matrix([[4], [7]]).scale(1.1).next_to(equals, m.RIGHT, buff=0.3)
        result.set_color(m.YELLOW)
        self.play(m.Transform(step, result))
        self.wait(2.0)
