# Source: docs/source/examples.rst
import manimgx as m


class RotationUpdater(m.Scene):
    def construct(self):
        def updater_forth(mobj, dt):
            mobj.rotate_about_origin(dt)

        def updater_back(mobj, dt):
            mobj.rotate_about_origin(-dt)

        line_reference = m.Line(m.ORIGIN, m.LEFT).set_color(m.WHITE)
        line_moving = m.Line(m.ORIGIN, m.LEFT).set_color(m.YELLOW)
        line_moving.add_updater(updater_forth)
        self.add(line_reference, line_moving)
        self.wait(2)
        line_moving.remove_updater(updater_forth)
        line_moving.add_updater(updater_back)
        self.wait(2)
        line_moving.remove_updater(updater_back)
        self.wait(0.5)
