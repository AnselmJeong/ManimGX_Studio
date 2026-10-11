# Source: manim/mobject/three_d/three_dimensions.py
import manimgx as m


class ExamplePrism(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=60 * m.DEGREES, theta=150 * m.DEGREES)
        prismSmall = m.Prism(dimensions=[1, 2, 3]).rotate(m.PI / 2)
        prismLarge = m.Prism(dimensions=[1.5, 3, 4.5]).move_to([2, 0, 0])
        self.add(prismSmall, prismLarge)
        self.wait()
