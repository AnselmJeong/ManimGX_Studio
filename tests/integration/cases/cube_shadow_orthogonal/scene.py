import math

import numpy as np

import manimgx as m


def cube_vertices(
    side: float, rot_axis: np.ndarray, rot_angle: float, offset: np.ndarray
) -> list[np.ndarray]:
    s = side / 2.0
    verts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                verts.append(np.array([sx * s, sy * s, sz * s]))
    axis = rot_axis / np.linalg.norm(rot_axis)
    c = math.cos(rot_angle)
    si = math.sin(rot_angle)
    K = np.array(
        [
            [0, -axis[2], axis[1]],
            [axis[2], 0, -axis[0]],
            [-axis[1], axis[0], 0],
        ]
    )
    R = np.eye(3) + si * K + (1 - c) * (K @ K)
    return [R @ v + offset for v in verts]


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)

        title = m.Tex("Cube shadow on the floor").to_corner(m.UL, buff=0.3)
        self.add_fixed_in_frame_mobjects(title)
        self.play(m.Write(title))

        floor = m.Square(
            side_length=4,
            color=m.GREY_B,
            stroke_width=1,
            fill_color=m.GREY_D,
            fill_opacity=0.4,
        )
        floor.shift(m.IN * 0.01)
        cube = m.Cube(
            side_length=1.4,
            fill_color=m.BLUE,
            fill_opacity=0.7,
            stroke_color=m.WHITE,
            stroke_width=1.5,
        )
        cube.shift(m.OUT * 0.8)
        cube.rotate(0.6, axis=np.array([1.0, 1.0, 0.3]))

        verts = cube_vertices(
            1.4, np.array([1.0, 1.0, 0.3]), 0.6, np.array([0.0, 0.0, 0.8])
        )
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        shadow = m.Polygon(
            [min(xs), min(ys), 0.001],
            [max(xs), min(ys), 0.001],
            [max(xs), max(ys), 0.001],
            [min(xs), max(ys), 0.001],
            color=m.BLACK,
            fill_color=m.BLACK,
            fill_opacity=0.55,
            stroke_width=1.5,
        )
        self.play(m.Create(floor))
        self.play(m.FadeIn(cube), m.FadeIn(shadow))

        drop_lines = m.VGroup()
        for v in verts:
            drop_lines.add(
                m.DashedLine(v, [v[0], v[1], 0.0], color=m.YELLOW, stroke_width=1.5)
            )
        self.play(m.Create(drop_lines))

        self.wait(2.0)
