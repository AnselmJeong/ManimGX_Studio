# Source: manimgx API coverage (CE 0.21 `LinearTransformationScene.apply_inverse`)
import manimgx as m


class ApplyInverseExample(m.LinearTransformationScene):
    def construct(self):
        self.add_vector([1, 2])
        self.apply_inverse([[2, 1], [1, 1]])
        self.wait(0.5)
