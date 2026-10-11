# Source: manim/utils/space_ops.py
import numpy as np

import manimgx as m


class SpaceOpsCoordTransformDemo(m.Scene):
    def construct(self):
        # cartesian_to_spherical: convert a few vectors to spherical and
        # plot dots whose positions encode (r, theta).
        cartesians = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([1.0, 1.0, 0.0]),
            np.array([0.0, 1.0, 1.0]),
        ]
        cart_origin = np.array([-5.0, 2.5, 0.0])
        sph_group = m.VGroup()
        for i, vec in enumerate(cartesians):
            spherical = m.cartesian_to_spherical(vec)
            radius_disp = float(spherical[0]) * 0.5
            theta_disp = float(spherical[1])
            x = cart_origin[0] + radius_disp * np.cos(theta_disp) + i * 1.2
            y = cart_origin[1] + radius_disp * np.sin(theta_disp)
            sph_group.add(m.Dot(np.array([x, y, 0.0]), color=m.BLUE, radius=0.08))

        # spherical_to_cartesian: round-trip back and draw a polygon.
        sph_inputs = [np.array([1.0, k * np.pi / 4, np.pi / 3]) for k in range(8)]
        cart_outputs = [m.spherical_to_cartesian(s) for s in sph_inputs]
        ring_pts = np.array(cart_outputs) + np.array([2.0, 2.5, 0.0])
        ring = m.Polygon(*ring_pts, color=m.GREEN)

        # complex_to_R3 / R3_to_complex: map a few complex numbers and plot.
        complexes = [1 + 0j, 0 + 1j, -1 + 0j, 0 - 1j, 1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]
        complex_origin = np.array([-3.0, -1.5, 0.0])
        complex_group = m.VGroup()
        for z in complexes:
            point = m.complex_to_R3(z)
            roundtrip = m.R3_to_complex(point)
            dot = m.Dot(complex_origin + 0.6 * point, color=m.YELLOW, radius=0.08)
            sign = 1 if roundtrip.real >= 0 else -1
            mark = m.Line(
                complex_origin + 0.6 * point,
                complex_origin + 0.6 * point + np.array([0.15 * sign, 0.0, 0.0]),
                color=m.RED,
                stroke_width=3,
            )
            complex_group.add(dot, mark)

        # complex_func_to_R3_func: build an R3 function from z -> z^2.
        r3_func = m.complex_func_to_R3_func(lambda z: z * z)
        func_origin = np.array([3.0, -1.5, 0.0])
        sample_inputs = [
            np.array([0.4 * np.cos(t), 0.4 * np.sin(t), 0.0])
            for t in np.linspace(0.0, 2 * np.pi, 12, endpoint=False)
        ]
        func_pts = [func_origin + r3_func(p) for p in sample_inputs]
        func_poly = m.Polygon(*func_pts, color=m.PURPLE)

        self.add(sph_group, ring, complex_group, func_poly)
        self.wait()
