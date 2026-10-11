# Source: example_scenes/basic.py
import manimgx as m


class LineJoints(m.Scene):
    def construct(self):
        t1 = m.Triangle()
        t2 = m.Triangle(joint_type=m.LineJointType.ROUND)
        t3 = m.Triangle(joint_type=m.LineJointType.BEVEL)

        grp = m.VGroup(t1, t2, t3).arrange(m.RIGHT)
        grp.set(width=m.config.frame_width - 1)

        self.add(grp)
        self.wait()
