import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Eigenvector scales by $\\lambda = 2$").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        plane = (
            m.NumberPlane(
                x_range=[-4, 4, 1],
                y_range=[-2.5, 2.5, 1],
                background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
            )
            .scale(0.9)
            .shift(m.DOWN * 0.4)
        )
        self.play(m.Create(plane))

        line = m.Line(
            plane.coords_to_point(-3, 3),
            plane.coords_to_point(3, -3),
            color=m.YELLOW,
            stroke_width=2.0,
        )
        self.play(m.Create(line))

        v = m.Arrow(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(-1, 1),
            color=m.GREEN,
            buff=0,
            stroke_width=4,
        )
        v_lab = (
            m.MathTex("\\mathbf v = (-1,1)", color=m.GREEN)
            .scale(0.65)
            .next_to(v.get_end(), m.UL, buff=0.1)
        )
        self.play(m.GrowArrow(v), m.Write(v_lab))

        v2 = m.Arrow(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(-2, 2),
            color=m.RED,
            buff=0,
            stroke_width=4,
        )
        v2_lab = (
            m.MathTex("A\\mathbf v = 2\\mathbf v", color=m.RED)
            .scale(0.65)
            .next_to(v2.get_end(), m.UL, buff=0.1)
        )
        self.play(m.Transform(v.copy(), v2), m.Write(v2_lab))

        eq = (
            m.MathTex(
                "A = \\begin{bmatrix} 3 & 1 \\\\ 0 & 2 \\end{bmatrix},\\quad"
                " \\lambda = 2",
                color=m.WHITE,
            )
            .scale(0.8)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(eq))
        self.wait(2.0)
