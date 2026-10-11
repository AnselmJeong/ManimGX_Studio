# Source: manimgx API coverage (CE 0.21 `VectorScene`)
import manimgx as m


class VectorSceneExample(m.VectorScene):
    def construct(self):
        self.add_plane(animate=True)
        self.play(m.Create(self.get_basis_vectors()))
        vector = self.add_vector([2, 1])
        self.label_vector(vector, "v")
        self.vector_to_coords(vector, clean_up=False)
