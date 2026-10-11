# Source: manim/mobject/geometry/arc.py
import manimgx as m


class UsefulAnnotations(m.Scene):
    def construct(self):
        m0 = m.Dot()
        m1 = m.AnnotationDot()
        m2 = m.LabeledDot("ii")
        m3 = m.LabeledDot(m.MathTex(r"\alpha").set_color(m.ORANGE))
        m4 = m.CurvedArrow(2 * m.LEFT, 2 * m.RIGHT, radius=-5)
        m5 = m.CurvedArrow(2 * m.LEFT, 2 * m.RIGHT, radius=8)
        m6 = m.CurvedDoubleArrow(m.ORIGIN, 2 * m.RIGHT)

        self.add(m0, m1, m2, m3, m4, m5, m6)
        for i, mobj in enumerate(self.mobjects):
            mobj.shift(m.DOWN * (i - 3))
        self.wait()
