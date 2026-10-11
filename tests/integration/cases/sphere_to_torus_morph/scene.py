"""Show me a sphere smoothly turning into a torus."""

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Using Scene.set_camera_orientation(phi=, theta=) for initial 3D view, "
    "then begin_ambient_camera_rotation / stop_ambient_camera_rotation for "
    "ambient azimuthal rotation (cross-engine: works on both manimgx's unified "
    "Scene and CE's ThreeDScene). Base class is m.ThreeDScene when available "
    "(CE), else m.Scene (manimgx)."
)


# Manim CE requires ThreeDScene for self.set_camera_orientation /
# begin_ambient_camera_rotation; manimgx's unified Scene already handles 3D
# and doesn't expose ThreeDScene.
_BaseScene = m.ThreeDScene


class TeacherScene(_BaseScene):
    def construct(self):
        sphere = m.Sphere(radius=2.0, resolution=(24, 24)).set_color(m.BLUE)
        sphere.set_opacity(0.7)

        torus = m.Torus(
            major_radius=2.0,
            minor_radius=0.6,
            resolution=(24, 24),
        )
        torus.set_opacity(0.7)

        # Initial 3D orientation
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)

        # Ambient azimuthal rotation so the morph reads from multiple angles.
        self.begin_ambient_camera_rotation(rate=0.3, about="theta")

        self.play(m.Create(sphere), run_time=2.5)
        self.wait(0.5)
        self.play(m.Transform(sphere, torus), run_time=4.0)
        self.wait(1.5)

        # Stop ambient rotation before final wait. Both engines default
        # `about` to "theta", so omit the kwarg — manimgx's stop signature
        # is just (self), while CE's is (self, about='theta').
        self.stop_ambient_camera_rotation()
        self.wait(0.5)
