# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class AntiderivativeExample(m.Scene):
    def construct(self):
        ax = m.Axes()
        graph1 = ax.plot(
            lambda x: (x**2 - 2) / 3,
            color=m.RED,
        )
        graph2 = ax.plot_antiderivative_graph(graph1, color=m.BLUE)
        self.add(ax, graph1, graph2)
        self.wait()
