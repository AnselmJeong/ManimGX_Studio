import manimgx as m


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-30 * m.DEGREES)
        axes = m.ThreeDAxes(
            x_range=[-2, 2, 1],
            y_range=[-2, 2, 1],
            z_range=[-2, 2, 1],
        )
        self.add(axes)

        title = m.Tex("Rotational symmetries of a cube").to_edge(m.UP, buff=0.3)
        self.add_fixed_in_frame_mobjects(title)

        cube = m.Cube(
            side_length=1.5, color=m.YELLOW, fill_opacity=0.55, stroke_width=2
        )
        self.play(m.FadeIn(cube))

        for axis in [m.UP, m.RIGHT, m.OUT, m.UR, m.UL]:
            self.play(cube.animate.rotate(m.PI / 2, axis=axis), run_time=1.2)
            self.wait(0.3)
        self.wait(1.0)
