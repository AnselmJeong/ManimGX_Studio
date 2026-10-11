# Regression: complete captured ray-tracing scenes rendered under Manim CE
# 0.20.1 but failed under manimgx when FadeIn scaled a Sphere copy.
import manimgx as m


class SphereFadeInScale(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=-35 * m.DEGREES)
        sphere = m.Sphere(radius=1.5, color=m.BLUE, fill_opacity=0.7)
        self.play(m.FadeIn(sphere, scale=0.8), run_time=0.5)
        self.wait(0.2)
