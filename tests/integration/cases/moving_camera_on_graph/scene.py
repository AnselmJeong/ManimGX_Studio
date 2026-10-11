# Source: manim/scene/moving_camera_scene.py
import numpy as np

import manimgx as m


def _scale_frame(frame, factor):
    frame.height *= factor
    return frame


def _ensure_frame_supports_scale(frame):
    if not hasattr(type(frame), "scale"):
        type(frame).scale = _scale_frame


class MovingCameraOnGraph(m.MovingCameraScene):
    def construct(self):
        self.camera.frame.save_state()

        ax = m.Axes(x_range=[-1, 10], y_range=[-1, 10])
        graph = ax.plot(np.sin, color=m.WHITE, x_range=[0, 3 * m.PI])

        dot_1 = m.Dot(ax.i2gp(graph.t_min, graph))
        dot_2 = m.Dot(ax.i2gp(graph.t_max, graph))
        self.add(ax, graph, dot_1, dot_2)

        _ensure_frame_supports_scale(self.camera.frame)
        self.play(self.camera.frame.animate.scale(0.5).move_to(dot_1))
        self.play(self.camera.frame.animate.move_to(dot_2))
        self.play(m.Restore(self.camera.frame))
        self.wait()
