# Source: manim/mobject/mobject.py
import manimgx as m


class CircleWithContent(m.VGroup):
    content: "m.Mobject | None"

    def __init__(self, content: "m.Mobject"):
        super().__init__()
        self.circle = m.Circle()
        self.content = content
        self.add(self.circle, content)
        content.move_to(self.circle.get_center())

    def clear_content(self):
        content = self.content
        if content is None:
            return
        self.remove(content)
        self.content = None

    @m.override_animate(clear_content)
    def _clear_content_animation(self, anim_args=None):
        if anim_args is None:
            anim_args = {}
        content = self.content
        if content is None:
            return m.Wait(run_time=0)
        anim = m.Uncreate(content, **anim_args)
        self.clear_content()
        return anim


class AnimationOverrideExample(m.Scene):
    def construct(self):
        t = m.Text("hello!")
        my_mobject = CircleWithContent(t)
        self.play(m.Create(my_mobject))
        self.play(my_mobject.animate.clear_content())  # ty: ignore[unresolved-attribute]
        self.wait()
