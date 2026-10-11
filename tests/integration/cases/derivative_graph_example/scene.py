# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class DerivativeGraphExample(m.Scene):
    def construct(self):
        ax = m.NumberPlane(
            y_range=[-1, 7],
            background_line_style={"stroke_opacity": 0.4},
        )

        curve_1 = ax.plot(lambda x: x**2, color=m.PURPLE_B)
        curve_2 = ax.plot_derivative_graph(curve_1)
        curves = m.VGroup(curve_1, curve_2)

        label_1 = ax.get_graph_label(curve_1, "x^2", x_val=-2, direction=m.DL)
        label_2 = ax.get_graph_label(curve_2, "2x", x_val=3, direction=m.RIGHT)
        labels = m.VGroup(label_1, label_2)

        self.add(ax, curves, labels)
        self.wait()
