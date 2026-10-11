# Source: manim/scene/moving_camera_scene.py
import manimgx as m


class MovingAndZoomingCamera(m.MovingCameraScene):
    def construct(self):
        s = m.Square(color=m.BLUE, fill_opacity=0.5).move_to(2 * m.LEFT)
        t = m.Triangle(color=m.YELLOW, fill_opacity=0.5).move_to(2 * m.RIGHT)
        self.add(s, t)
        self.play(self.camera.frame.animate.move_to(s).set(width=s.width * 2))
        self.wait(0.3)
        self.play(self.camera.frame.animate.move_to(t).set(width=t.width * 2))

        self.play(self.camera.frame.animate.move_to(m.ORIGIN).set(width=14))
