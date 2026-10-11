# Source: docs/source/guides/deep_dive.rst
import manimgx as m


class VMobjectDemo(m.Scene):
    def construct(self):
        plane = m.NumberPlane()
        my_vmobject = m.VMobject(color=m.GREEN).set_points(
            [
                [-2, -1, 0],  # start of first curve
                [-3, 1, 0],
                [0, 3, 0],
                [1, 3, 0],  # end of first curve
                [1, 3, 0],  # start of second curve
                [0, 1, 0],
                [4, 3, 0],
                [4, -2, 0],  # end of second curve
            ]
        )
        handles = [
            m.Dot(point, color=m.RED)
            for point in [[-3, 1, 0], [0, 3, 0], [0, 1, 0], [4, 3, 0]]
        ]
        handle_lines = [
            m.Line(
                my_vmobject.points[ind],
                my_vmobject.points[ind + 1],
                color=m.RED,
                stroke_width=2,
            )
            for ind in range(0, len(my_vmobject.points), 2)
        ]
        self.add(plane, *handles, *handle_lines, my_vmobject)
        self.wait()
