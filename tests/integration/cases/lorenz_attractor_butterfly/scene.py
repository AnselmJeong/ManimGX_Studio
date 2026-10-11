"""Show me the Lorenz attractor — let me watch the butterfly shape form as the trajectory traces out."""

import math

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Pre-integrated trajectory hand-rolled (Euler) to avoid scipy dependency. "
    "manimgx Camera lacks reorient(theta, phi, gamma); using "
    "Scene.set_camera_orientation(phi=..., theta=...) instead. "
    "Base class is m.ThreeDScene when available (CE), else m.Scene (manimgx), "
    "since manimgx's unified Scene already handles 3D."
)


# Manim CE requires ThreeDScene for self.set_camera_orientation; manimgx's
# unified Scene already handles 3D and doesn't expose ThreeDScene.
_BaseScene = m.ThreeDScene


class TeacherScene(_BaseScene):
    def construct(self):
        # Lorenz parameters
        sigma = 10.0
        rho = 28.0
        beta = 8.0 / 3.0

        # Euler integration of the Lorenz system
        dt = 0.005
        n_steps = 4000
        state = np.array([0.1, 0.0, 0.0])
        trajectory: list[np.ndarray] = [state.copy()]
        for _ in range(n_steps):
            x, y, z = state
            dx = sigma * (y - x)
            dy = x * (rho - z) - y
            dz = x * y - beta * z
            state = state + dt * np.array([dx, dy, dz])
            trajectory.append(state.copy())

        # Build ThreeDAxes sized for the Lorenz range (roughly x,y in [-25,25], z in [0,50])
        axes = m.ThreeDAxes(
            x_range=(-30.0, 30.0, 10.0),
            y_range=(-30.0, 30.0, 10.0),
            z_range=(0.0, 50.0, 10.0),
            x_length=6.0,
            y_length=6.0,
            z_length=5.0,
        )

        # Normalize trajectory into axes coordinates
        # Parametrize by index -> sample a smooth curve via ParametricFunction in 3D
        traj_arr = np.asarray(trajectory)

        def path_func(t: float) -> np.ndarray:
            # t in [0, 1] maps linearly to trajectory index
            idx_f = t * (len(traj_arr) - 1)
            idx = math.floor(idx_f)
            frac = idx_f - idx
            if idx >= len(traj_arr) - 1:
                pt = traj_arr[-1]
            else:
                pt = traj_arr[idx] * (1.0 - frac) + traj_arr[idx + 1] * frac
            return np.asarray(axes.c2p(float(pt[0]), float(pt[1]), float(pt[2])))

        curve = m.ParametricFunction(
            path_func,
            t_range=(0.0, 1.0, 1.0 / 1200.0),
            color=m.BLUE,
            stroke_width=2.0,
        ).set_shade_in_3d(True)

        # Set a 3D camera orientation before any play
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=40 * m.DEGREES)

        self.play(m.Create(axes), run_time=1.5)
        self.play(m.Create(curve, rate_func=m.linear), run_time=8.0)
        self.wait(0.5)
