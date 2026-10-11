"""Show me a tangent vector field on a sphere — arrows wrapping around it."""

import math

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "manimgx Camera lacks reorient(theta, phi, gamma); using "
    "Scene.set_camera_orientation(phi=..., theta=...) for 3D view. "
    "Streamlines on the surface skipped — no surface-bound StreamLines API. "
    "Base class is m.ThreeDScene when available (CE), else m.Scene (manimgx)."
)


# Manim CE requires ThreeDScene for self.set_camera_orientation; manimgx's
# unified Scene already handles 3D and doesn't expose ThreeDScene.
_BaseScene = m.ThreeDScene


class TeacherScene(_BaseScene):
    def construct(self):
        radius = 1.5
        sphere = m.Sphere(radius=radius).set_opacity(0.5)

        # Fibonacci-like distribution of points on the sphere, build a tangent
        # vector field: azimuthal flow projected to the tangent plane.
        n_points = 30
        arrows: list[m.Arrow3D] = []
        golden = math.pi * (1.0 + math.sqrt(5.0))
        for i in range(n_points):
            phi = math.acos(1.0 - 2.0 * (i + 0.5) / n_points)
            theta = golden * i
            # Point on sphere
            sp = np.array(
                [
                    radius * math.sin(phi) * math.cos(theta),
                    radius * math.sin(phi) * math.sin(theta),
                    radius * math.cos(phi),
                ]
            )
            # Outward normal
            normal = sp / float(np.linalg.norm(sp))
            # Azimuthal direction in 3D (tangent to lines of latitude)
            azimuthal = np.array([-math.sin(theta), math.cos(theta), 0.0])
            # Project out any normal component (ensure tangency)
            tangent = azimuthal - float(np.dot(azimuthal, normal)) * normal
            norm = float(np.linalg.norm(tangent))
            if norm < 1e-6:
                # Near poles: fall back to a non-azimuthal tangent
                ref = np.array([1.0, 0.0, 0.0])
                tangent = ref - float(np.dot(ref, normal)) * normal
                norm = float(np.linalg.norm(tangent))
            tangent = tangent / norm * 0.35

            start = sp
            end = sp + tangent
            arrow = m.Arrow3D(
                start=start,
                end=end,
                color=m.YELLOW,
            )
            arrows.append(arrow)

        m.VGroup(*arrows)

        self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)

        self.play(m.FadeIn(sphere), run_time=1.5)
        self.play(
            m.LaggedStart(
                *[m.Create(a) for a in arrows],
                lag_ratio=0.05,
            ),
            run_time=5.0,
        )
        self.wait(0.5)
