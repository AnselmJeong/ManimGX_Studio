"""Show the 6th roots of unity as omega^k = e^(2 pi i k / 6) marching around the unit circle."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        plane = m.ComplexPlane(
            x_range=(-2.0, 2.0, 1.0),
            y_range=(-2.0, 2.0, 1.0),
        ).scale(1.0)

        origin_pt = plane.n2p(0.0 + 0.0j)
        unit_pt = plane.n2p(1.0 + 0.0j)
        radius = float(np.linalg.norm(unit_pt - origin_pt))

        unit_circle = m.Circle(radius=radius, color=m.TEAL).move_to(origin_pt)

        N = 6
        roots = [np.exp(m.TAU * 1j * k / N) for k in range(N)]
        dots = m.VGroup(
            *[m.Dot(plane.n2p(z), radius=0.09, color=m.YELLOW) for z in roots]
        )
        radii = m.VGroup(
            *[
                m.Line(origin_pt, plane.n2p(z), stroke_color=m.BLUE, stroke_width=2.0)
                for z in roots
            ]
        )
        labels = m.VGroup()
        for k, z in enumerate(roots):
            lbl = m.MathTex(Rf"\omega^{{{k}}}").scale(0.6)
            point = plane.n2p(z)
            # Push label radially outward from origin
            direction = point - origin_pt
            norm = float(np.linalg.norm(direction))
            offset = direction / max(norm, 1e-9) * 0.35
            lbl.move_to(point + offset)
            labels.add(lbl)

        self.play(m.Create(plane), run_time=1.0)
        self.play(m.Create(unit_circle), run_time=0.8)
        self.play(
            m.LaggedStart(
                *[
                    m.AnimationGroup(
                        m.GrowFromCenter(dot),
                        m.Create(radius_line),
                        m.Write(label),
                    )
                    for dot, radius_line, label in zip(dots, radii, labels, strict=True)
                ],
                lag_ratio=0.2,
            ),
            run_time=3.0,
        )

        walker = m.MathTex(R"\omega^k").scale(0.8).set_color(m.RED)
        walker.move_to(plane.n2p(roots[0]) + 0.5 * m.UP)
        self.play(m.FadeIn(walker), run_time=0.4)
        for k in range(1, N + 1):
            target_idx = k % N
            target_point = plane.n2p(roots[target_idx])
            target = walker.copy().move_to(target_point + 0.5 * m.UP)
            self.play(
                m.Transform(walker, target, path_arc=m.TAU / N),
                run_time=0.6,
            )
        self.wait(0.5)
