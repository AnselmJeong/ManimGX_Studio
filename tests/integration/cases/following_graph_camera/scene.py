# Source: docs/source/examples.rst
import numpy as np

import manimgx as m


def _scale_frame(frame, factor):
    frame.height *= factor
    return frame


def _ensure_frame_supports_scale(frame):
    if not hasattr(type(frame), "scale"):
        type(frame).scale = _scale_frame


class FollowingGraphCamera(m.MovingCameraScene):
    def construct(self):
        self.camera.frame.save_state()

        # create the axes and the curve
        ax = m.Axes(x_range=[-1, 10], y_range=[-1, 10])
        graph = ax.plot(np.sin, color=m.BLUE, x_range=[0, 3 * m.PI])

        # create dots based on the graph
        moving_dot = m.Dot(ax.i2gp(graph.t_min, graph), color=m.ORANGE)
        dot_1 = m.Dot(ax.i2gp(graph.t_min, graph))
        dot_2 = m.Dot(ax.i2gp(graph.t_max, graph))

        self.add(ax, graph, dot_1, dot_2, moving_dot)
        _ensure_frame_supports_scale(self.camera.frame)
        self.play(self.camera.frame.animate.scale(0.5).move_to(moving_dot))

        def update_curve(mob):
            mob.move_to(moving_dot.get_center())

        self.camera.frame.add_updater(update_curve)
        self.play(m.MoveAlongPath(moving_dot, graph, rate_func=m.linear))
        self.camera.frame.remove_updater(update_curve)

        self.play(m.Restore(self.camera.frame))
