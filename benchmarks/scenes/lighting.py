"""Linked-rings camera, material and key light."""

import math

import numpy as np

TIME = 2.5
PHI = math.radians(65)
THETA = math.radians(-45) + 0.24 * TIME
VIEW = np.array(
    [math.sin(PHI) * math.cos(THETA), math.sin(PHI) * math.sin(THETA), math.cos(PHI)]
)
RIGHT = np.array([-math.sin(THETA), math.cos(THETA), 0])
UP = np.cross(VIEW, RIGHT)


def unit(value):
    return value / np.linalg.norm(value)


LIGHTS = [(unit(0.8 * VIEW + 0.9 * UP - 0.6 * RIGHT), 1.0, True)]
ROUGHNESS = 0.5
