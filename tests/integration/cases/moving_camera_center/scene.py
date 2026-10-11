# Source: manim/scene/moving_camera_scene.py
import manimgx as m


class MovingCameraCenter(m.MovingCameraScene):
    def construct(self):
        s = m.Square(color=m.RED, fill_opacity=0.5).move_to(2 * m.LEFT)
        t = m.Triangle(color=m.GREEN, fill_opacity=0.5).move_to(2 * m.RIGHT)
        self.wait(0.3)
        self.add(s, t)
        self.play(self.camera.frame.animate.move_to(s))
        self.wait(0.3)
        self.play(self.camera.frame.animate.move_to(t))
