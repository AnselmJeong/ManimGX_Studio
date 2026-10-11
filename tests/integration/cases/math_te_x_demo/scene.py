# Source: docs/source/guides/using_text.rst
import manimgx as m


def _math_xrightarrow(font_size):
    if m.__name__ == "manimgx":
        return m.Tex(r"$\xrightarrow{x^6y^8}$", font_size=font_size)
    return m.MathTex(r"\xrightarrow{x^6y^8}", font_size=font_size)


class MathTeXDemo(m.Scene):
    def construct(self):
        rtarrow0 = _math_xrightarrow(font_size=96)
        rtarrow1 = m.Tex(r"$\xrightarrow{x^6y^8}$", font_size=96)

        self.add(m.VGroup(rtarrow0, rtarrow1).arrange(m.DOWN))
