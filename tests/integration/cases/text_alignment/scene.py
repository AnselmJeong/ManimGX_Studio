# Source: manim/mobject/text/text_mobject.py
import manimgx as m


class TextAlignment(m.Scene):
    def construct(self):
        title = m.Text("K-means clustering and Logistic Regression", color=m.WHITE)
        title.scale(0.75)
        self.add(title.to_edge(m.UP))

        t1 = m.Text("1. Measuring").set_color(m.WHITE)

        t2 = m.Text("2. Clustering").set_color(m.WHITE)

        t3 = m.Text("3. Regression").set_color(m.WHITE)

        t4 = m.Text("4. Prediction").set_color(m.WHITE)

        x = (
            m.VGroup(t1, t2, t3, t4)
            .arrange(direction=m.DOWN, aligned_edge=m.LEFT)
            .scale(0.7)
            .next_to(m.ORIGIN, m.DR)
        )
        x.set_opacity(0.5)
        x.submobjects[1].set_opacity(1)
        self.add(x)
        self.wait()
