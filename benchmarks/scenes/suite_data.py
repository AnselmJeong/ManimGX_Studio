"""Geometry and output settings for the five animation scenes."""

import numpy as np

SECONDS = 3.0
WIDTH, HEIGHT, FPS = 1920, 1080, 60
COLORS = ("#58C4DD", "#FC6255", "#83C167", "#FFFF00", "#9A72AC")
DURATIONS = {
    "orbit": 10.0,
    "matrix": 7.2,
    "pendulums": 13.0,
    "hierarchy": 3.0,
    "linked_rings": 3.0,
}


def planet_position(i, t):
    angle = 2 * np.pi * i / 5 + (0.45 + 0.08 * i) * t
    return np.array(
        [2.5 * np.cos(angle), 2.5 * np.sin(angle), 0.35 * np.sin(2 * angle)]
    )


def moon_position(i, t):
    angle = 2.4 * t + i
    return planet_position(i, t) + 0.5 * np.array(
        [np.cos(angle), np.sin(angle), np.sin(angle)]
    )


def torus_point(u, v):
    radius = 0.58 + 0.11 * np.cos(v)
    return np.array([radius * np.cos(u), radius * np.sin(u), 0.11 * np.sin(v)])


def rotation_x(angle):
    c, s = (np.cos(angle), np.sin(angle))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ring_pose(i, t):
    rotation = rotation_x(i % 2 * np.pi / 2 + 0.12 * np.sin(t + i * 0.3))
    position = np.array(
        [0.75 * (i - 3.5), 0.12 * np.sin(t + i * 0.3), 0.2 * np.sin(0.8 * t + i * 0.5)]
    )
    return (rotation, position)
