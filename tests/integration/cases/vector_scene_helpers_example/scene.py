# Source: manimgx API coverage (CE 0.21 `VectorScene helpers`)
import manimgx as m


class VectorSceneHelpersExample(m.VectorScene):
    def construct(self):
        self.add_plane().fade(0.7)
        self.add_axes()
        self.add(self.get_basis_vector_labels())
        vector = self.add_vector([2, -1], color=m.TEAL)
        self.write_vector_coordinates(vector)
        self.wait(0.5)
