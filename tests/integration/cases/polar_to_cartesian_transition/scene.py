import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Polar grid $\\to$ Cartesian grid")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        polar = m.PolarPlane(radius_max=3.0, size=6)
        self.add(polar)
        self.wait(0.5)

        cart = m.NumberPlane(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=6,
            y_length=6,
        )
        self.play(m.Transform(polar, cart), run_time=2.5)
        self.wait(1.5)
