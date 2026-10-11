# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class VectorFieldNudgeSubmobjectsAndMovement(m.Scene):
    def construct(self):
        field = m.ArrowVectorField(
            lambda p: np.array([np.cos(p[1]), np.sin(p[0]), 0.0]),
            x_range=[-2, 2, 1.0],
            y_range=[-2, 2, 1.0],
        )
        # Nudge submobjects positionally with the renamed ``mob`` kwarg.
        field.nudge(mob=field, dt=0.1, substeps=2)
        field.nudge_submobjects(dt=0.05, substeps=1)
        # Start and stop continuous movement to verify both methods round-trip.
        field.start_submobject_movement(speed=0.5)
        field.stop_submobject_movement()
        self.add(field)
        self.wait(0.1)
