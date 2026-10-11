# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class CoordsToPointExample(m.Scene):
    def construct(self):
        ax = m.Axes().add_coordinates()

        # a dot with respect to the axes
        dot_axes = m.Dot(ax.coords_to_point(2, 2), color=m.GREEN)
        lines = ax.get_lines_to_point(ax.c2p(2, 2))

        # a dot with respect to the scene
        # the default plane corresponds to the coordinates of the scene.
        plane = m.NumberPlane()
        dot_scene = m.Dot((2, 2, 0), color=m.RED)

        self.add(plane, dot_scene, ax, dot_axes, lines)
        self.wait()
