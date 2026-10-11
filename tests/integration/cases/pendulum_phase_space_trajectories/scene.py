import math

import numpy as np

import manimgx as m

G = 9.8
L = 1.0


def field(theta: float, omega: float) -> np.ndarray:
    return np.array([omega, -G / L * math.sin(theta), 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Pendulum phase space: $\\theta$ vs $\\omega$")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        plane = m.NumberPlane(
            x_range=[-math.pi * 1.5, math.pi * 1.5, math.pi / 2],
            y_range=[-5, 5, 1],
            x_length=12,
            y_length=6,
        )
        self.add(plane)

        arrows = m.VGroup()
        for theta in np.arange(-math.pi * 1.2, math.pi * 1.21, 0.55):
            for omega in np.arange(-4, 4.1, 1.0):
                vec = field(theta, omega)
                norm = np.linalg.norm(vec)
                if norm < 0.1:
                    continue
                scale = 0.32 / max(norm, 0.5)
                start = plane.coords_to_point(theta, omega)
                end = plane.coords_to_point(
                    theta + scale * vec[0], omega + scale * vec[1]
                )
                arrows.add(
                    m.Arrow(
                        start,
                        end,
                        color=m.GREY,
                        buff=0,
                        stroke_width=1.5,
                        max_tip_length_to_length_ratio=0.3,
                    ),
                )
        self.play(m.FadeIn(arrows), run_time=1.5)

        theta_v, omega_v = 2.0, 0.0
        dt = 0.02
        points: list[np.ndarray] = [plane.coords_to_point(theta_v, omega_v)]
        for _ in range(400):
            theta_v += dt * omega_v
            omega_v += -dt * G / L * math.sin(theta_v)
            if abs(theta_v) > math.pi * 1.3 or abs(omega_v) > 4.5:
                break
            points.append(plane.coords_to_point(theta_v, omega_v))

        trajectory = m.VMobject(stroke_color=m.YELLOW, stroke_width=3)
        trajectory.set_points_as_corners(points)
        self.play(m.Create(trajectory), run_time=3.0)
        self.wait(1.5)
