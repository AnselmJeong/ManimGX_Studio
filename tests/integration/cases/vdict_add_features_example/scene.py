# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VDictAddFeaturesExample(m.Scene):
    def construct(self):
        registry = m.VDict(
            mapping_or_iterable={
                "circle": m.Circle(radius=0.5, color=m.RED),
                "square": m.Square(side_length=1.0, color=m.GREEN),
            }
        )
        registry.add_key_value_pair("triangle", m.Triangle(color=m.BLUE).scale(0.5))
        members = m.Group(*registry.get_all_submobjects()).arrange(m.RIGHT, buff=0.5)
        self.add(members)
        self.wait()
