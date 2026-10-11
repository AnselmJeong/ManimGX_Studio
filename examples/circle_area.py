"""Why a circle's area is πr²: unroll it.

Cut a disc of radius r into thin rings. Each ring, cut at the top and unrolled, is a thin strip
as long as its circumference, 2πρ for the ring of radius ρ, and as thick as the ring. Stack the
strips, the longest at the bottom: their lengths shrink evenly from 2πr to 0, so they make a
right triangle with base 2πr and height r. Its area is ½ · 2πr · r = πr², and so is the disc's:
the thinner the rings, the closer the stack to the triangle.
"""

import numpy as np

import manimgx as m

WALL = 3.4  # the rings unroll and stack

N = 24  # rings
R = 1.9  # the disc's radius, in scene units
DR = R / N  # each ring's thickness
CENTER = np.array([-3.4, 1.75, 0])  # the disc's
CORNER = np.array([-5.55, -2.95, 0])  # the triangle's right angle, bottom left
RINGS = m.color_gradient([m.BLUE, m.TEAL, m.GREEN], N)  # inside out
RADIUS = m.YELLOW  # r, the radius and the triangle's height
ROUND = m.GREEN  # 2πr, the outermost ring and the triangle's base
SAMPLES = 121


def ring_points(rho: float, unrolled: float, bottom: np.ndarray) -> np.ndarray:
    """The ring of radius `rho`, `unrolled` from 0 (a circle) to 1 (a straight strip): an arc
    of radius rho/(1 − unrolled) and angle 2π(1 − unrolled), so as long as the circle, whose
    lowest point stays at `bottom`, with its tangent level there."""
    s = np.linspace(-np.pi * rho, np.pi * rho, SAMPLES)  # arc length from the bottom
    k = (1 - unrolled) / rho  # the curvature
    # sin(ks)/k and (1 − cos(ks))/k, written to stay exact as k → 0
    x = s * np.sinc(k * s / np.pi)
    y = 0.5 * k * s**2 * np.sinc(k * s / (2 * np.pi)) ** 2
    return bottom + np.stack([x, y, np.zeros_like(s)], axis=1)


class CircleArea(m.Scene):
    def construct(self) -> None:
        radii = [(k + 0.5) * DR for k in range(N)]

        def ring(
            k: int, unrolled: float = 0.0, bottom: np.ndarray | None = None
        ) -> m.VMobject:
            rho = radii[k]
            where = CENTER - rho * m.UP if bottom is None else bottom
            mob = m.VMobject(stroke_color=RINGS[k], stroke_width=100 * DR * 0.88)
            mob.set_points_as_corners(ring_points(rho, unrolled, where))
            return mob

        disc = m.VGroup(*[ring(k) for k in range(N)])
        radius = m.Line(CENTER, CENTER + R * m.RIGHT, color=RADIUS, stroke_width=6)
        r_label = m.MathTex("r", color=RADIUS, font_size=56)
        r_label.next_to(radius, m.RIGHT, buff=0.18)  # at its end, clear of the rings

        radius.set_z_index(1)  # over the rings, and over their copies as they leave
        r_label.set_z_index(1)
        # 0–3 s: the disc, swept out
        self.play(*[m.Create(r) for r in disc], run_time=1.6)
        self.play(
            m.Create(radius), m.FadeIn(r_label, shift=0.2 * m.RIGHT), run_time=0.9
        )

        # 3–9 s: each ring, cut at the top, unrolls as it falls into its place in the
        # stack: the longest at the bottom, every strip starting at the triangle's left edge
        progress = [m.ValueTracker(0.0) for _ in range(N)]

        def strip(k: int) -> m.VMobject:
            u = progress[k].get_value()
            rho = radii[k]
            start = CENTER - rho * m.UP
            end = CORNER + np.pi * rho * m.RIGHT + (R - rho) * m.UP
            return ring(k, min(1.0, u / 0.75), start + u * (end - start))

        strips = m.VGroup(*[m.always_redraw(lambda k=k: strip(k)) for k in range(N)])
        self.add(strips)
        self.play(
            m.LaggedStart(
                *[progress[k].animate.set_value(1.0) for k in reversed(range(N))],
                lag_ratio=0.07,
            ),
            run_time=6.5,
        )

        # 9–11 s: the stack is a right triangle, 2πr wide and r tall
        top = CORNER + R * m.UP
        right = CORNER + 2 * np.pi * R * m.RIGHT
        outline = m.Polygon(CORNER, right, top, color=m.WHITE, stroke_width=3)
        base = m.Line(CORNER, right)
        height = m.Line(CORNER, top)
        base_brace = m.Brace(base, m.DOWN, buff=0.12, color=ROUND)
        base_label = m.MathTex(r"2\pi r", color=ROUND, font_size=52)
        base_label.next_to(base_brace, m.DOWN, buff=0.1)
        height_brace = m.Brace(height, m.LEFT, buff=0.12, color=RADIUS)
        height_label = m.MathTex("r", color=RADIUS, font_size=52)
        height_label.next_to(height_brace, m.LEFT, buff=0.12)
        self.play(m.Create(outline), run_time=1)
        self.play(
            m.GrowFromCenter(base_brace),
            m.FadeIn(base_label, shift=0.2 * m.DOWN),
            m.GrowFromCenter(height_brace),
            m.FadeIn(height_label, shift=0.2 * m.LEFT),
            run_time=1.2,
        )

        # 11–18 s: the area, half the base times the height
        area = m.MathTex(
            r"{{\text{Area} =}} {{\frac{1}{2} \cdot 2}} {{\pi}} {{r}} \cdot {{r}}",
            font_size=60,
        )
        area[1][-1].set_color(ROUND)  # the 2 of 2πr (its glyphs: 1, 2, bar, dot, 2)
        m.VGroup(area[2], area[3]).set_color(ROUND)
        area[5].set_color(RADIUS)
        area.move_to(np.array([2.9, CENTER[1], 0]))
        cancelled = m.MathTex(
            r"{{\text{Area} =}} {{\pi}} {{r}} \cdot {{r}}", font_size=60
        )
        m.VGroup(cancelled[1], cancelled[2]).set_color(ROUND)
        cancelled[4].set_color(RADIUS)
        cancelled.move_to(area, aligned_edge=m.LEFT)
        result = m.MathTex(r"{{\text{Area} =}} {{\pi}} {{r}}^{ {{2}} }", font_size=72)
        m.VGroup(result[1], result[2]).set_color(ROUND)
        result.get_parts_by_tex("2", substring=False).set_color(RADIUS)
        result.move_to(area)

        self.play(m.Write(area), run_time=1.5)
        self.wait(0.5)
        # ½ and 2 cancel
        self.play(
            m.FadeOut(area[1], shift=0.3 * m.DOWN),
            *[
                m.ReplacementTransform(a, b)
                for a, b in zip([area[0], *area[2:]], cancelled, strict=True)
            ],
            run_time=1.2,
        )
        self.remove(*cancelled)
        self.add(cancelled)
        # r · r = r²
        self.play(m.TransformMatchingTex(cancelled, result), run_time=1.5)
        self.wait(2)


if __name__ == "__main__":
    CircleArea().render("circle_area.mp4")
