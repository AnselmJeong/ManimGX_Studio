# Source: docs/source/tutorials/building_blocks.rst
import numpy as np

import manimgx as m


class MobjectExample(m.Scene):
    def construct(self):
        p1 = [-1, -1, 0]
        p2 = [1, -1, 0]
        p3 = [1, 1, 0]
        p4 = [-1, 1, 0]
        a = m.VMobject().set_points_as_corners([p1, p2, p3, p4])
        point_start = a.get_start()
        point_end = a.get_end()
        point_center = a.get_center()
        self.add(
            m.Text(
                f"a.get_start() = {np.round(point_start, 2).tolist()}",
                font_size=24,
            )
            .to_edge(m.UR)
            .set_color(m.YELLOW)
        )
        self.add(
            m.Text(f"a.get_end() = {np.round(point_end, 2).tolist()}", font_size=24)
            .next_to(self.mobjects[-1], m.DOWN)
            .set_color(m.RED)
        )
        self.add(
            m.Text(
                f"a.get_center() = {np.round(point_center, 2).tolist()}",
                font_size=24,
            )
            .next_to(self.mobjects[-1], m.DOWN)
            .set_color(m.BLUE)
        )

        self.add(m.Dot(a.get_start()).set_color(m.YELLOW).scale(2))
        self.add(m.Dot(a.get_end()).set_color(m.RED).scale(2))
        self.add(m.Dot(a.get_top()).set_color(m.GREEN_A).scale(2))
        self.add(m.Dot(a.get_bottom()).set_color(m.GREEN_D).scale(2))
        self.add(m.Dot(a.get_center()).set_color(m.BLUE).scale(2))
        self.add(m.Dot(a.point_from_proportion(0.5)).set_color(m.ORANGE).scale(2))
        self.add(*[m.Dot(x) for x in a.points])
        self.add(a)
        self.wait()
