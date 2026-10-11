# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class AddIterableToVGroupExample(m.Scene):
    def construct(self):
        v = m.VGroup(
            m.Square(),  # Singular VMobject instance
            [m.Circle(), m.Triangle()],  # List of VMobject instances
            m.Dot(),
            (m.Dot() for _ in range(2)),  # Iterable that generates VMobjects
        )
        v.arrange()
        self.add(v)
        self.wait()
