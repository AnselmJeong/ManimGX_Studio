# Source: manim/scene/zoomed_scene.py
import manimgx as m


class ChangingZoomScale(m.ZoomedScene):
    def __init__(self, **kwargs):
        m.ZoomedScene.__init__(
            self,
            zoom_factor=0.3,
            zoomed_display_height=1,
            zoomed_display_width=3,
            image_frame_stroke_width=20,
            zoomed_camera_config={
                "default_frame_stroke_width": 3,
            },
            **kwargs,
        )

    def construct(self):
        dot = m.Dot().set_color(m.GREEN)
        sq = m.Circle(fill_opacity=1, radius=0.2).next_to(dot, m.RIGHT)
        self.add(dot, sq)
        self.wait(1)
        self.activate_zooming(animate=False)
        self.wait(1)
        self.play(dot.animate.shift(m.LEFT * 0.3))

        self.play(self.zoomed_camera.frame.animate.scale(4))
        self.play(self.zoomed_camera.frame.animate.shift(0.5 * m.DOWN))
