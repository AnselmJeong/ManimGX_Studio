"""Show multiplication by i as a rotation on the complex plane."""

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self):
        plane = m.ComplexPlane(
            x_range=(-3.0, 3.0, 1.0),
            y_range=(-3.0, 3.0, 1.0),
        ).scale(0.9)

        z = m.ComplexValueTracker(1 + 0j)
        dot = m.Dot(color=m.YELLOW, radius=0.12)
        dot.add_updater(lambda d: d.move_to(z.points))

        label = m.MathTex(R"z \cdot i").scale(1.0)
        label.to_corner(m.UR, buff=0.5)

        self.play(m.Create(plane), run_time=1.5)
        self.play(m.Write(label), run_time=0.8)
        self.add(dot)
        self.play(z.animate.set_value(1j), run_time=1.0)
        self.play(z.animate.set_value(-1 + 0j), run_time=1.0)
        self.play(z.animate.set_value(-1j), run_time=1.0)
        self.play(z.animate.set_value(1 + 0j), run_time=1.0)
        self.wait(0.5)
