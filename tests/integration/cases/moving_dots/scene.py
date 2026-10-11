# Source: docs/source/examples.rst
import manimgx as m


class MovingDots(m.Scene):
    def construct(self):
        d1, d2 = m.Dot(color=m.BLUE), m.Dot(color=m.GREEN)
        dg = m.VGroup(d1, d2).arrange(m.RIGHT, buff=1)
        l1 = m.Line(d1.get_center(), d2.get_center()).set_color(m.RED)
        x = m.ValueTracker(0)
        y = m.ValueTracker(0)
        d1.add_updater(lambda z: z.set_x(x.get_value()))
        d2.add_updater(lambda z: z.set_y(y.get_value()))
        l1.add_updater(lambda z: z.become(m.Line(d1.get_center(), d2.get_center())))
        self.add(d1, d2, l1)
        self.play(x.animate.set_value(5))
        self.play(y.animate.set_value(4))
        self.wait()
