# Source: manim/animation/animation.py
import manimgx as m


class DefaultAddScene(m.Scene):
    def construct(self):
        text_1 = m.Text("I was added with Add!")
        text_2 = m.Text("Me too!")
        text_3 = m.Text("And me!")
        texts = m.VGroup(text_1, text_2, text_3).arrange(m.DOWN)
        rect = m.SurroundingRectangle(texts, buff=0.5)

        self.play(
            m.Create(rect, run_time=3.0),
            m.Succession(
                m.Wait(1.0),
                # You can Add a Mobject in the middle of an animation...
                m.Add(text_1),
                m.Wait(1.0),
                # ...or multiple Mobjects at once!
                m.Add(text_2, text_3),
            ),
        )
        self.wait()
