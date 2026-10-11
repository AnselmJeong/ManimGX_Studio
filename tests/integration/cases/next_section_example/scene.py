# Source: manimgx API coverage (CE 0.21 `Scene.next_section`)
import manimgx as m


class NextSectionExample(m.Scene):
    def construct(self):
        self.next_section("intro")
        circle = m.Circle(color=m.TEAL)
        self.play(m.Create(circle))
        self.next_section("change")
        self.play(m.Transform(circle, m.Square(color=m.ORANGE)))
        self.next_section("outro")
        self.play(m.FadeOut(circle))
