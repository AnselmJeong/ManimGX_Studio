# Source: manimgx API coverage (CE 0.21 `LinearTransformationScene helpers`)
import manimgx as m


class LinearTransformationHelpersExample(m.LinearTransformationScene):
    def __init__(self):
        super().__init__(show_coordinates=True, leave_ghost_vectors=True)

    def construct(self):
        self.add_title("A shear")
        self.add_unit_square()
        vector = self.add_vector([1, 2])
        self.add_transformable_label(vector, "v", animate=False)
        self.apply_matrix([[1, 1], [0, 1]])
        self.wait(0.5)
