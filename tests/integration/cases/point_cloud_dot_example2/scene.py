# Source: manim/mobject/types/point_cloud_mobject.py
import random

import numpy as np

import manimgx as m


class PointCloudDotExample2(m.Scene):
    def construct(self):
        plane = m.ComplexPlane()
        random.seed(0)
        cloud = m.PointCloudDot(color=m.RED)
        self.add(plane, cloud)
        self.wait()
        self.play(
            m.ApplyPointwiseFunction(
                lambda point: m.complex_to_R3(np.exp(m.R3_to_complex(point))),
                cloud,
            )
        )
