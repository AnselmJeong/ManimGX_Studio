# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetSecantSlopeGroupExample(m.Scene):
    def construct(self):
        ax = m.Axes(y_range=[-1, 7])
        graph = ax.plot(lambda x: 1 / 4 * x**2, color=m.BLUE)
        slopes = ax.get_secant_slope_group(
            x=2.0,
            graph=graph,
            dx=1.0,
            dx_label=m.Tex("dx = 1.0"),
            dy_label="dy",
            dx_line_color=m.GREEN_B,
            secant_line_length=4,
            secant_line_color=m.RED_D,
        )

        self.add(ax, graph, slopes)
        self.wait()
