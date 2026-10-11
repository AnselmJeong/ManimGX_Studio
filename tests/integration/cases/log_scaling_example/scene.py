# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class LogScalingExample(m.Scene):
    def construct(self):
        ax = m.Axes(
            x_range=[0, 10, 1],
            y_range=[-2, 6, 1],
            tips=False,
            axis_config={"include_numbers": True},
            y_axis_config={"scaling": m.LogBase(custom_labels=True)},
        )

        # x_min must be > 0 because log is undefined at 0.
        graph = ax.plot(lambda x: x**2, x_range=[0.001, 10], use_smoothing=False)
        self.add(ax, graph)
        self.wait()
