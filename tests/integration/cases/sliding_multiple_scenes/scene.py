# Source: manim/scene/moving_camera_scene.py
import manimgx as m


class SlidingMultipleScenes(m.MovingCameraScene):
    def construct(self):
        def create_scene(number):
            frame = m.Rectangle(width=16, height=9)
            circ = m.Circle().shift(m.LEFT)
            text = m.Tex(f"This is Scene {number!s}").next_to(circ, m.RIGHT)
            frame.add(circ, text)
            return frame

        group = m.VGroup(*(create_scene(i) for i in range(4))).arrange_in_grid(buff=4)
        self.add(group)
        self.camera.auto_zoom(group[0], animate=False)
        for scene in group:
            self.play(self.camera.auto_zoom(scene))
            self.wait()

        self.play(self.camera.auto_zoom(group, margin=2))
