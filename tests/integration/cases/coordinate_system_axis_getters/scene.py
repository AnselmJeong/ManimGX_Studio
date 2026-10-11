# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class CoordinateSystemAxisGetters(m.Scene):
    def construct(self):
        axes = m.Axes(
            x_range=(-3, 3, 1),
            y_range=(-2, 2, 1),
            x_length=6,
            y_length=4,
            tips=False,
        )
        assert axes.get_x_axis() is axes.get_axis(0)
        assert axes.get_y_axis() is axes.get_axis(1)
        assert list(axes.get_axes()) == [axes.get_x_axis(), axes.get_y_axis()]

        try:
            axes.get_z_axis()
        except IndexError:
            pass
        else:
            raise AssertionError("2D Axes.get_z_axis() must raise IndexError")

        axes_3d = m.ThreeDAxes(
            x_range=(-2, 2, 1),
            y_range=(-2, 2, 1),
            z_range=(-2, 2, 1),
            x_length=4,
            y_length=4,
            z_length=4,
        )
        getters = (
            axes_3d.get_x_axis,
            axes_3d.get_y_axis,
            axes_3d.get_z_axis,
        )
        for index, getter in enumerate(getters):
            assert getter() is axes_3d.get_axis(index)
        assert list(axes_3d.get_axes()) == [getter() for getter in getters]

        self.add(axes)
        self.wait()
