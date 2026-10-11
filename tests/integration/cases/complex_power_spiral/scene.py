import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Powers of $z = 1 + i$ spiral outward")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        plane = m.NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            x_length=10,
            y_length=10,
        )
        self.add(plane)

        z = complex(1, 1)
        points = [plane.coords_to_point(0, 0)]
        for k in range(1, 8):
            val = z**k
            if abs(val) > 5:
                break
            points.append(plane.coords_to_point(val.real, val.imag))

        for i in range(1, len(points)):
            line = m.Line(points[i - 1], points[i], color=m.YELLOW, stroke_width=2)
            dot = m.Dot(points[i], color=m.RED, radius=0.1)
            self.play(m.Create(line), m.FadeIn(dot), run_time=0.5)
        self.wait(2.0)
