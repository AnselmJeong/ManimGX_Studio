"""Orbiting planets and animated linked rings in the native Manim APIs."""

import os

import numpy as np
from lighting import LIGHTS, ROUGHNESS
from suite_data import (
    COLORS,
    SECONDS,
    moon_position,
    planet_position,
    ring_pose,
    torus_point,
)

ENGINE = os.environ.get("BENCH_ENGINE", "manimgx")
if ENGINE == "manimgl":
    import manimlib as m
elif ENGINE == "manim_ce":
    import manim as m
else:
    import manimgx as m
GL = ENGINE == "manimgl"


def sphere(radius, color, resolution=(16, 8)):
    if GL:
        return m.Sphere(
            radius=radius, color=color, resolution=tuple(n + 1 for n in resolution)
        )
    return m.Sphere(
        radius=radius,
        resolution=resolution,
        color=color,
        fill_color=color,
        fill_opacity=1,
        stroke_width=0,
        checkerboard_colors=False,
    )


def torus(color):
    if GL:
        return m.ParametricSurface(
            torus_point,
            u_range=(0, 2 * np.pi),
            v_range=(0, 2 * np.pi),
            resolution=(33, 9),
            color=color,
        )
    obj = m.Surface(
        torus_point,
        u_range=(0, 2 * np.pi),
        v_range=(0, 2 * np.pi),
        resolution=(32, 8),
        fill_color=color,
        fill_opacity=1,
        checkerboard_colors=False,
        stroke_width=0,
    )
    if ENGINE == "manimgx":
        obj.set_material(m.Material(metallic=0, roughness=ROUGHNESS, reflectance=0.5))
    return obj


def build_objects(name, duration=SECONDS):
    objects, updates = ([], [])
    if name == "hierarchy":
        objects.append(sphere(0.65, COLORS[3]))
        for i in range(5):
            planet, moon = (sphere(0.28, COLORS[i]), sphere(0.1, "#DDDDDD", (8, 4)))
            objects.extend([planet, moon])
            updates.extend(
                [
                    (planet, lambda obj, t, i=i: obj.move_to(planet_position(i, t))),
                    (moon, lambda obj, t, i=i: obj.move_to(moon_position(i, t))),
                ]
            )
    else:
        for i in range(8):
            base = torus(COLORS[i % 5])
            obj = base.copy()
            objects.append(obj)

            def update_pose(obj, t, i=i, base=base):
                rotation, position = ring_pose(i, t)
                obj.become(base.copy().apply_matrix(rotation).shift(position))

            updates.append((obj, update_pose))
    return (objects, updates)


class Benchmark(m.ThreeDScene):
    def construct(self):
        name = os.environ["BENCH_SCENE"]
        duration = float(os.environ.get("BENCH_DURATION", SECONDS))
        timer = m.ValueTracker(0)
        if GL:
            self.frame.reorient(45, 65)
            self.frame.set_focal_distance(20)
            self.frame.add_updater(lambda frame, dt: frame.increment_theta(0.24 * dt))
        else:
            self.set_camera_orientation(phi=65 * m.DEGREES, theta=-45 * m.DEGREES)
            self.begin_ambient_camera_rotation(rate=0.24)
        if name == "linked_rings":
            self.camera.light_source.move_to(LIGHTS[0][0] * 10000)
            if ENGINE == "manimgx":
                self.camera.tone_mapping = "linear"
                self.camera.exposure = 1
                self.camera.bloom = 0
                self.camera.ambient_occlusion = 0
                for direction, intensity, shadows in LIGHTS:
                    self.add(
                        m.SunLight(direction, intensity=intensity, shadows=shadows)
                    )
        objects, updates = build_objects(name, duration)

        def update_all(_):
            for obj, update in updates:
                update(obj, timer.get_value())

        update_all(timer)
        driver = m.Mobject().add_updater(update_all)
        self.add(*objects, timer, driver)
        self.play(
            timer.animate.set_value(duration), run_time=duration, rate_func=m.linear
        )
