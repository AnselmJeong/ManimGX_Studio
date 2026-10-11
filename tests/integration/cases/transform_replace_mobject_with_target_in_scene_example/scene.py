# Source: manim/animation/transform.py
import manimgx as m


class TransformReplaceMobjectWithTargetInSceneExample(m.Scene):
    def construct(self):
        source = m.Square(color=m.BLUE, fill_opacity=1.0)
        target = m.Circle(color=m.RED, fill_opacity=1.0)
        self.add(source)
        self.play(
            m.Transform(
                source,
                target,
                replace_mobject_with_target_in_scene=True,
            )
        )
        self.play(target.animate.shift(2 * m.RIGHT))
