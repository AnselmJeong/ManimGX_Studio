import manimgx as m

X = 1.5
DX = 0.45


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-35 * m.DEGREES)
        axes = m.ThreeDAxes(
            x_range=[0, 3, 1],
            y_range=[0, 3, 1],
            z_range=[0, 3, 1],
        )
        self.add(axes)

        cube = m.Cube(side_length=X, color=m.YELLOW, fill_opacity=0.55, stroke_width=2)
        cube.move_to([X / 2, X / 2, X / 2])
        self.play(m.FadeIn(cube))

        label = m.MathTex("V = x^3", color=m.YELLOW).to_corner(m.UR, buff=0.5)
        self.add_fixed_in_frame_mobjects(label)
        self.wait(0.5)

        slab_top = m.Prism(
            dimensions=[X, X, DX], color=m.BLUE, fill_opacity=0.55, stroke_width=1
        ).move_to([X / 2, X / 2, X + DX / 2])
        slab_right = m.Prism(
            dimensions=[DX, X, X], color=m.GREEN, fill_opacity=0.55, stroke_width=1
        ).move_to([X + DX / 2, X / 2, X / 2])
        slab_front = m.Prism(
            dimensions=[X, DX, X], color=m.RED, fill_opacity=0.55, stroke_width=1
        ).move_to([X / 2, X + DX / 2, X / 2])
        slabs = m.VGroup(slab_top, slab_right, slab_front)
        self.play(m.FadeIn(slabs), run_time=1.5)

        new_label = m.MathTex(
            "dV \\approx 3 x^2 \\, dx",
            color=m.YELLOW,
        ).to_corner(m.UR, buff=0.5)
        self.add_fixed_in_frame_mobjects(new_label)
        self.play(m.Transform(label, new_label))
        self.wait(2.0)
