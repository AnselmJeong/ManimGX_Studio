"""A surface plot on 3D axes, a curve drawn across it with a ball riding its tip, and the
camera circling the whole time: every frame is new. (ManimGL.)"""

import tempfile

import numpy as np
from manimlib import *
from PIL import Image

YELLOW, BLUE_E = "#F7D96F", "#236B8E"  # Manim CE's colors, where ManimGL's differ


def checkerboard(colors: list[str], cells: int = 48, px: int = 16) -> str:
    """A PNG of `cells` x `cells` squares: ManimGL's surfaces take one color, so the
    checkerboard is painted on as a texture (face (i, j) gets colors[(i + j) % 2])."""
    a, b = (color_to_int_rgb(c) for c in colors)
    rows, cols = np.indices((cells, cells))
    image = np.where(((rows + cols + 1) % 2 == 0)[..., None], a, b).astype(np.uint8)
    path = f"{tempfile.gettempdir()}/checkerboard.png"
    Image.fromarray(image.repeat(px, 0).repeat(px, 1)).save(path)
    return path


class Orbit(ThreeDScene):
    default_camera_config = {"background_color": BLACK}

    def construct(self) -> None:
        axes = ThreeDAxes(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            z_range=(-2, 2, 1),
            width=7,
            height=7,
            depth=4,
            axis_config={"include_tip": True},
        )
        surface = TexturedSurface(
            ParametricSurface(
                lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
                u_range=(-3, 3),
                v_range=(-3, 3),
                resolution=(49, 49),  # sample points: 48 x 48 squares
            ),
            checkerboard([BLUE_D, BLUE_E]),
        )
        curve = ParametricCurve(
            lambda t: axes.c2p(
                2.4 * np.cos(t),
                2.4 * np.sin(t),
                np.sin(2.4 * np.cos(t)) * np.cos(2.4 * np.sin(t)) + 0.08,
            ),
            t_range=(
                0,
                TAU,
                0.01,
            ),  # Manim CE's sampling (ManimGL's default step is 0.1)
            color=YELLOW,
            stroke_width=6,
        )
        ball = Sphere(radius=0.12, color=YELLOW).move_to(curve.get_start())
        self.frame.reorient(45, 65)  # ManimGL's theta is Manim CE's plus 90 degrees
        self.frame.set_focal_distance(20)  # Manim CE's camera distance
        self.add(axes, surface, ball)
        self.frame.add_updater(lambda frame, dt: frame.increment_theta(0.3 * dt))
        self.play(
            ShowCreation(curve),
            MoveAlongPath(ball, curve),
            run_time=6,
            rate_func=linear,
        )
        self.wait(4)
