# Source: docs/source/examples.rst
import numpy as np

import manimgx as m


class MovingZoomedSceneAround(m.ZoomedScene):
    # contributed by TheoremofBeethoven, www.youtube.com/c/TheoremofBeethoven
    def __init__(self, **kwargs):
        m.ZoomedScene.__init__(
            self,
            zoom_factor=0.3,
            zoomed_display_height=1,
            zoomed_display_width=6,
            image_frame_stroke_width=20,
            zoomed_camera_config={
                "default_frame_stroke_width": 3,
            },
            **kwargs,
        )

    def construct(self):
        dot = m.Dot().shift(m.UL * 2)
        image = m.ImageMobject(
            np.array([[0, 100, 30, 200], [255, 0, 5, 33]], dtype=np.uint8)
        )
        image.height = 7
        frame_text = m.Text("Frame", color=m.PURPLE, font_size=67)
        zoomed_camera_text = m.Text("Zoomed camera", color=m.RED, font_size=67)

        self.add(image, dot)
        zoomed_camera = self.zoomed_camera
        zoomed_display = self.zoomed_display
        frame = zoomed_camera.frame
        zoomed_display_frame = zoomed_display.display_frame

        frame.move_to(dot)
        frame.set_color(m.PURPLE)
        zoomed_display_frame.set_color(m.RED)
        zoomed_display.shift(m.DOWN)

        zd_rect = m.BackgroundRectangle(
            zoomed_display, fill_opacity=0, buff=m.MED_SMALL_BUFF
        )
        self.add_foreground_mobject(zd_rect)

        unfold_camera = m.UpdateFromFunc(
            zd_rect, lambda rect: rect.replace(zoomed_display)
        )

        frame_text.next_to(frame, m.DOWN)

        self.play(m.Create(frame), m.FadeIn(frame_text, shift=m.UP))
        self.activate_zooming()

        self.play(self.get_zoomed_display_pop_out_animation(), unfold_camera)
        zoomed_camera_text.next_to(zoomed_display_frame, m.DOWN)
        self.play(m.FadeIn(zoomed_camera_text, shift=m.UP))
        # Scale in        x   y  z
        scale_factor = [0.5, 1.5, 0]
        self.play(
            frame.animate.scale(scale_factor),
            zoomed_display.animate.scale(scale_factor),
            m.FadeOut(zoomed_camera_text),
            m.FadeOut(frame_text),
        )
        self.wait()
        self.play(m.ScaleInPlace(zoomed_display, 2))
        self.wait()
        self.play(frame.animate.shift(2.5 * m.DOWN))
        self.wait()
        self.play(
            self.get_zoomed_display_pop_out_animation(),
            unfold_camera,
            rate_func=lambda t: m.smooth(1 - t),
        )
        self.play(m.Uncreate(zoomed_display_frame), m.FadeOut(frame))
        self.wait()
