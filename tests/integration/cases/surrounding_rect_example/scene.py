# Source: manim/mobject/geometry/shape_matchers.py
import manimgx as m


class SurroundingRectExample(m.Scene):
    def construct(self):
        title = m.Title("A Quote from Newton")
        quote = m.Text(
            "If I have seen further than others, \n"
            "it is by standing upon the shoulders of giants.",
            color=m.BLUE,
        ).scale(0.75)
        box = m.SurroundingRectangle(quote, color=m.YELLOW, buff=m.MED_LARGE_BUFF)

        t2 = m.Tex(r"Hello World").scale(1.5)
        box2 = m.SurroundingRectangle(t2, corner_radius=0.2)
        mobjects = m.VGroup(m.VGroup(box, quote), m.VGroup(t2, box2)).arrange(m.DOWN)
        self.add(title, mobjects)
        self.wait()
