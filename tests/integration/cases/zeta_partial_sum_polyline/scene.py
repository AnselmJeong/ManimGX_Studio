"""Show the Riemann zeta partial sum as a chain of complex vectors. Sweep s from 1.5 toward the first nontrivial zero."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        plane = m.ComplexPlane(
            x_range=(-2.0, 2.0, 1.0),
            y_range=(-1.0, 2.0, 1.0),
        ).scale(0.8)

        N = 20
        s_tracker = m.ComplexValueTracker(complex(1.5, 0.0))

        def build_polyline() -> m.VMobject:
            s = s_tracker.get_value()
            summands = np.array(
                [1.0 / (n**s) for n in range(1, N + 1)],
                dtype=complex,
            )
            partial_sums = np.concatenate([[0.0 + 0.0j], np.cumsum(summands)])
            points = [plane.n2p(z) for z in partial_sums]
            path = m.VMobject()
            path.set_points_as_corners(points)
            path.set_stroke(m.TEAL, width=3.0)
            return path

        def build_endpoint() -> m.Dot:
            s = s_tracker.get_value()
            summands = np.array(
                [1.0 / (n**s) for n in range(1, N + 1)],
                dtype=complex,
            )
            total = complex(summands.sum())
            return m.Dot(plane.n2p(total), radius=0.08, color=m.YELLOW)

        path = m.always_redraw(build_polyline)
        endpoint = m.always_redraw(build_endpoint)

        title = m.MathTex(R"\sum_{n=1}^{20} \frac{1}{n^s}").scale(0.9)
        title.to_corner(m.UR, buff=0.4)

        self.play(m.Create(plane), run_time=1.2)
        self.play(m.Write(title), run_time=0.8)
        self.add(path, endpoint)
        self.wait(0.5)
        self.play(
            s_tracker.animate.set_value(complex(0.5, 14.134)),
            run_time=4.0,
        )
        self.wait(0.5)
