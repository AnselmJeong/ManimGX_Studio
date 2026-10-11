import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Block collisions in $(x_1, x_2)$ phase space",
            )
            .scale(0.8)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        plane = m.NumberPlane(
            x_range=[0, 6, 1],
            y_range=[0, 5, 1],
            x_length=9,
            y_length=6,
        ).shift(m.LEFT * 0.5)
        self.add(plane)

        diag = m.Line(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(5, 5),
            color=m.GREY,
            stroke_width=2,
        )
        diag_label = (
            m.Tex(
                "$x_1 = x_2$ (collision)",
                color=m.GREY,
            )
            .scale(0.55)
            .move_to(plane.coords_to_point(3, 3.5))
        )
        self.play(m.Create(diag), m.Write(diag_label))

        x1, x2 = 5.0, 4.0
        v1, v2 = -0.8, -1.2
        dt = 0.05
        path_points = [plane.coords_to_point(x1, x2)]
        for _ in range(220):
            x1 += dt * v1
            x2 += dt * v2
            if x1 < 0:
                x1 = 0
                v1 = -v1
            if x2 < x1:
                v1, v2 = v2, v1
            path_points.append(plane.coords_to_point(x1, x2))
            if x1 > 5 or x2 > 5:
                break

        trajectory = m.VMobject(stroke_color=m.YELLOW, stroke_width=3)
        trajectory.set_points_as_corners(path_points)
        self.play(m.Create(trajectory), run_time=3.0)
        self.wait(1.5)
