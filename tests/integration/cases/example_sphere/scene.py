# Source: manim/mobject/three_d/three_dimensions.py
import manimgx as m


class ExampleSphere(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=m.PI / 6, theta=m.PI / 6)
        sphere1 = m.Sphere(
            center=(3, 0, 0),
            radius=1,
            resolution=(20, 20),
            u_range=[0.001, m.PI - 0.001],
            v_range=[0, m.TAU],
        )
        sphere1.set_color(m.RED)
        self.add(sphere1)
        sphere2 = m.Sphere(center=(-1, -3, 0), radius=2, resolution=(18, 18))
        sphere2.set_color(m.GREEN)
        self.add(sphere2)
        sphere3 = m.Sphere(center=(-1, 2, 0), radius=2, resolution=(16, 16))
        sphere3.set_color(m.BLUE)
        self.add(sphere3)
        self.wait()
