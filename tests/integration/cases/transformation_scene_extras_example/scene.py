# Source: manimgx API coverage (CE 0.21 `LinearTransformationScene helpers`)
import manimgx as m


class TransformationSceneExtrasExample(m.LinearTransformationScene):
    def __init__(self):
        super().__init__(leave_ghost_vectors=True)

    def construct(self):
        self.add_vector(self.get_vector([1, 1], color=m.PINK))
        vector = self.add_vector([-1, 2])
        self.write_vector_coordinates(vector)
        rotation = self.get_matrix_transformation([[0, -1], [1, 0]])
        self.add(m.Dot(rotation(2 * m.RIGHT), color=m.YELLOW))
        self.apply_inverse_transpose([[1, 1], [0, 1]])
        self.play(m.Indicate(self.get_ghost_vectors()))
