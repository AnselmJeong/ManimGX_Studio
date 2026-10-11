# Source: manim/scene/moving_camera_scene.py
import manimgx as m


class ChangingCameraWidthAndRestore(m.MovingCameraScene):
    def construct(self):
        text = m.Text("Hello World").set_color(m.BLUE)
        self.add(text)
        self.camera.frame.save_state()
        self.play(self.camera.frame.animate.set(width=text.width * 1.2))
        self.wait(0.3)
        self.play(m.Restore(self.camera.frame))
