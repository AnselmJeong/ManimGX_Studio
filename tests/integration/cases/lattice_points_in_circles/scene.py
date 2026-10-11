import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            x_length=8,
            y_length=8,
        )
        self.add(plane)

        lattice = m.VGroup()
        for x in range(-5, 6):
            for y in range(-5, 6):
                lattice.add(
                    m.Dot(plane.coords_to_point(x, y), color=m.GREY, radius=0.05),
                )
        self.play(m.FadeIn(lattice), run_time=0.8)

        r = m.ValueTracker(0.5)
        origin = plane.coords_to_point(0, 0)
        unit = plane.coords_to_point(1, 0)[0] - origin[0]

        circle = m.always_redraw(
            lambda: m.Circle(
                radius=r.get_value() * unit,
                color=m.YELLOW,
                stroke_width=3,
            ).move_to(origin),
        )

        def highlighted() -> m.VGroup:
            radius = r.get_value()
            inside = m.VGroup()
            for x in range(-5, 6):
                for y in range(-5, 6):
                    if x * x + y * y <= radius * radius:
                        inside.add(
                            m.Dot(
                                plane.coords_to_point(x, y), color=m.YELLOW, radius=0.09
                            ),
                        )
            return inside

        def count_label() -> m.MathTex:
            radius = r.get_value()
            count = sum(
                1
                for x in range(-5, 6)
                for y in range(-5, 6)
                if x * x + y * y <= radius * radius
            )
            return m.MathTex(
                f"N(r) = {count}",
                color=m.YELLOW,
            ).to_corner(m.UR, buff=0.5)

        self.add(circle, m.always_redraw(highlighted), m.always_redraw(count_label))
        self.play(r.animate.set_value(4.6), run_time=5.5, rate_func=m.linear)
        self.wait(1.2)
