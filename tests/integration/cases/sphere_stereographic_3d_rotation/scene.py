import manimgx as m


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-30 * m.DEGREES)
        axes = m.ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-3, 3, 1],
        )
        self.add(axes)

        title = m.Tex("Sphere in 3D, rotating about the y-axis").to_edge(m.UP, buff=0.3)
        self.add_fixed_in_frame_mobjects(title)

        sphere = m.Sphere(radius=2.0, color=m.BLUE, fill_opacity=0.45)
        self.play(m.FadeIn(sphere))
        sphere.add_updater(lambda mob, dt: mob.rotate(dt * 2 * m.PI / 5.0, axis=m.UP))
        self.wait(5.0)
        sphere.clear_updaters()
        self.wait(0.5)
