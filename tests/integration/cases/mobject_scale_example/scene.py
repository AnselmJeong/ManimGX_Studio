# Source: manim/mobject/mobject.py
import manimgx as m


class MobjectScaleExample(m.Scene):
    def construct(self):
        f1 = m.Text("F")
        f2 = m.Text("F").scale(2)
        f3 = m.Text("F").scale(0.5)
        f4 = m.Text("F").scale(-1)

        vgroup = m.VGroup(f1, f2, f3, f4).arrange(6 * m.RIGHT)
        self.add(vgroup)
        self.wait()
