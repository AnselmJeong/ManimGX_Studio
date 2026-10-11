"""Show stereographic projection: dots on a sphere project down through the north pole onto a plane."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "frame.reorient unavailable in manimgx; using "
    "Scene.set_camera_orientation(phi=...) for the slight tilt — works on "
    "both manimgx's unified Scene and CE's ThreeDScene. Base class is "
    "m.ThreeDScene when available (CE), else m.Scene (manimgx)."
)


# Manim CE requires ThreeDScene for self.set_camera_orientation; manimgx's
# unified Scene already handles 3D and doesn't expose ThreeDScene.
_BaseScene = m.ThreeDScene


class TeacherScene(_BaseScene):
    def construct(self):
        sphere = m.Sphere(radius=1.0).set_opacity(0.4)
        sphere.shift(0.5 * m.UP)

        plane = (
            m.NumberPlane(
                x_range=(-3.0, 3.0, 1.0),
                y_range=(-3.0, 3.0, 1.0),
            )
            .scale(0.6)
            .shift(2.0 * m.DOWN)
        )

        # North pole in world coordinates (sphere radius 1, shifted 0.5 up)
        north_pole = np.array([0.0, 0.0, 1.0]) + 0.5 * m.UP
        ground_z = float(plane.get_center()[2])

        n_dots = 8
        sphere_points: list[np.ndarray] = []
        plane_points: list[np.ndarray] = []
        for k in range(n_dots):
            theta = m.TAU * k / n_dots
            pt_on_sphere = np.array([np.cos(theta), np.sin(theta), 0.0]) + 0.5 * m.UP
            sphere_points.append(pt_on_sphere)
            direction = pt_on_sphere - north_pole
            # Parametrize: north_pole + t * direction, find t s.t. z = ground_z
            denom = float(direction[2])
            if abs(denom) < 1e-9:
                projected = np.array([pt_on_sphere[0], pt_on_sphere[1], ground_z])
            else:
                t = (ground_z - float(north_pole[2])) / denom
                projected = north_pole + t * direction
            plane_points.append(projected)

        sphere_dots = m.VGroup(
            *[m.Dot(pt, radius=0.08, color=m.YELLOW) for pt in sphere_points]
        )
        rays = m.VGroup(
            *[
                m.Line(north_pole, pt, stroke_color=m.TEAL, stroke_width=1.5)
                for pt in sphere_points
            ]
        )
        plane_dots = m.VGroup(
            *[m.Dot(pt, radius=0.08, color=m.YELLOW) for pt in plane_points]
        )
        np_marker = m.Dot(north_pole, radius=0.09, color=m.RED)

        self.play(m.FadeIn(sphere), m.Create(plane), run_time=1.5)
        # A small polar tilt so the sphere reads as a 3D ball above the plane.
        self.set_camera_orientation(phi=20.0 * m.DEGREES)
        self.play(m.FadeIn(np_marker), m.FadeIn(sphere_dots), run_time=1.0)
        self.play(m.Create(rays), run_time=2.0)
        self.play(
            m.LaggedStart(
                *[
                    m.TransformFromCopy(sd, pd)
                    for sd, pd in zip(sphere_dots, plane_dots, strict=False)
                ],
                lag_ratio=0.5,
            ),
            run_time=3.0,
        )
        self.wait(1.0)
        self.wait(0.5)
