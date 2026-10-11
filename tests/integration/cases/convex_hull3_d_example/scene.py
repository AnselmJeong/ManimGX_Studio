# Source: manim/mobject/three_d/polyhedra.py
import manimgx as m


class ConvexHull3DExample(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        points = [
            [1.93192757, 0.44134585, -1.52407061],
            [-0.93302521, 1.23206983, 0.64117067],
            [-0.44350918, -0.61043677, 0.21723705],
            [-0.42640268, -1.05260843, 1.61266094],
            [-1.84449637, 0.91238739, -1.85172623],
            [1.72068132, -0.11880457, 0.51881751],
            [0.41904805, 0.44938012, -1.86440686],
            [0.83864666, 1.66653337, 1.88960123],
            [0.22240514, -0.80986286, 1.34249326],
            [-1.29585759, 1.01516189, 0.46187522],
            [1.7776499, -1.59550796, -1.70240747],
            [0.80065226, -0.12530398, 1.70063977],
            [1.28960948, -1.44158255, 1.39938582],
            [-0.93538943, 1.33617705, -0.24852643],
            [-1.54868271, 1.7444399, -0.46170734],
        ]
        hull = m.ConvexHull3D(
            *points,
            faces_config={"stroke_opacity": 0},
            graph_config={
                "vertex_type": m.Dot3D,
                "edge_config": {
                    "stroke_color": m.BLUE,
                    "stroke_width": 2,
                    "stroke_opacity": 0.05,
                },
            },
        )
        dots = m.VGroup(*[m.Dot3D(point) for point in points])
        self.add(hull)
        self.add(dots)
        self.wait()
