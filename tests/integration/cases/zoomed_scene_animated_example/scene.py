# Source: manimgx API coverage (CE 0.21 `ZoomedScene.activate_zooming(animate=True)`)
import manimgx as m


class ZoomedSceneAnimatedExample(m.ZoomedScene):
    def construct(self):
        dot = m.Dot(color=m.YELLOW).shift(2 * m.UL)
        self.add(m.NumberPlane(), dot)
        self.zoomed_camera.frame.move_to(dot)
        self.activate_zooming(animate=True)
        self.wait(0.5)
