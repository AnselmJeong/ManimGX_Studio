# Source: docs/source/examples.rst
import manimgx as m


class MovingFrameBox(m.Scene):
    def construct(self):
        text = m.MathTex(
            "\\frac{d}{dx}f(x)g(x)=",
            "f(x)\\frac{d}{dx}g(x)",
            "+",
            "g(x)\\frac{d}{dx}f(x)",
        )
        self.play(m.Write(text))
        framebox1 = m.SurroundingRectangle(text[1], buff=0.1)
        framebox2 = m.SurroundingRectangle(text[3], buff=0.1)
        self.play(
            m.Create(framebox1),
        )
        self.wait()
        self.play(
            m.Transform(framebox1, framebox2),
        )
        self.wait()
