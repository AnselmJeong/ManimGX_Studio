# Source: manim/constants.py
import numpy as np

import manimgx as m


class LineJointVariants(m.Scene):
    def construct(self):
        mob = m.VMobject(stroke_width=20, color=m.GREEN).set_points_as_corners(
            [
                np.array([-2, 0, 0]),
                np.array([0, 0, 0]),
                np.array([-2, 1, 0]),
            ]
        )
        lines = m.VGroup(*[mob.copy() for _ in range(len(m.LineJointType))])
        for line, joint_type in zip(lines, m.LineJointType):
            line.joint_type = joint_type

        lines.arrange(m.RIGHT, buff=1)
        self.add(lines)
        for line, joint_type in zip(lines, m.LineJointType):
            label = m.Text(joint_type.name).next_to(line, m.DOWN)
            self.add(label)
