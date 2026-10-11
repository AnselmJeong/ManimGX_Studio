# Source: manim/scene/vector_space_scene.py
import manimgx as m


class LinearTransformationSceneExample(m.LinearTransformationScene):
    def __init__(self, **kwargs):
        m.LinearTransformationScene.__init__(
            self, show_coordinates=True, leave_ghost_vectors=True, **kwargs
        )

    def construct(self):
        matrix = [[1, 1], [0, 1]]
        self.apply_matrix(matrix)
        self.wait()
