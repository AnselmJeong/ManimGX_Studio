"""Circles on circles draw π.

Any closed curve is a sum of circular motions. Let z(t) be a point of the complex plane that
goes once around the curve as t runs from 0 to 1; then z(t) = Σ cₙ e^{2πint}. Each term is an
arrow of length |cₙ| that turns n times while the curve is traced once: put the arrows tip to
tail, and the last tip runs along the curve. Each cₙ is measured from the curve itself,
cₙ = ∫ z(t) e^{−2πint} dt, here from the outline of the letter π. With 101 arrows the drawing
can't be told from the letter (3Blue1Brown, "But what is a Fourier series?", 2019).
"""

import numpy as np

import manimgx as m

TERMS = 50  # the frequencies −TERMS … TERMS
PERIOD = 10.0  # seconds the arrows take to draw the curve once
SAMPLES = 4096  # points along the outline, evenly spaced
WALL = 5.0  # the README wall's 5 seconds start here


def outline(glyph: m.Mobject) -> np.ndarray:
    """`SAMPLES` points evenly spaced along a closed outline, as complex numbers."""
    curves = glyph.points.reshape(-1, 4, 3)[:, :, :2]
    s = np.linspace(0, 1, 64, endpoint=False)[None, :, None]
    p0, p1, p2, p3 = (curves[:, k][:, None] for k in range(4))
    dense = (
        (1 - s) ** 3 * p0
        + 3 * (1 - s) ** 2 * s * p1
        + 3 * (1 - s) * s**2 * p2
        + s**3 * p3
    ).reshape(-1, 2)
    closed = np.vstack([dense, dense[:1]])
    run = np.concatenate(
        [[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
    )
    at = np.linspace(0, run[-1], SAMPLES, endpoint=False)
    return np.interp(at, run, closed[:, 0]) + 1j * np.interp(at, run, closed[:, 1])


def coefficients(z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The frequencies 0, 1, −1, 2, −2, … and their coefficients cₙ, by the discrete transform."""
    spectrum = np.fft.fft(z) / len(z)
    order = [0] + [n for k in range(1, TERMS + 1) for n in (k, -k)]
    frequencies = np.array(order)
    return frequencies, spectrum[frequencies % len(z)]


def to_point(z: complex | np.ndarray) -> np.ndarray:
    z = np.asarray(z)
    return np.stack([z.real, z.imag, np.zeros_like(z.real)], axis=-1)


class FourierPi(m.Scene):
    def construct(self) -> None:
        letter = m.MathTex(r"\pi").scale_to_fit_height(5.0).move_to(0.55 * m.UP)
        glyph = letter.family_members_with_points()[0]
        frequencies, c = coefficients(outline(glyph))
        clock = m.ValueTracker(0.0)  # laps of the curve

        def tips(t: float) -> np.ndarray:
            """The chain's joints after t laps: its start, then each arrow's tip."""
            turns = c * np.exp(m.TAU * 1j * frequencies * t)
            return np.concatenate([[0], np.cumsum(turns)])

        # each arrow keeps its shape (|cₙ| doesn't change) and only turns and moves
        arrows = m.VGroup()
        circles = m.VGroup()
        bases: list[list[np.ndarray]] = []
        for coefficient in c[1:]:
            size = abs(coefficient)
            arrow = m.Arrow(
                m.ORIGIN,
                size * m.RIGHT,
                buff=0,
                stroke_width=2.5,
                tip_length=0.2,
                max_tip_length_to_length_ratio=0.25,
                max_stroke_width_to_length_ratio=12,
                color=m.GREY_A,
            )
            bases.append(
                [part.points.copy() for part in arrow.family_members_with_points()]
            )
            arrows.add(arrow)
            circles.add(
                m.Circle(
                    radius=size, stroke_width=1.5, stroke_opacity=0.6, color=m.BLUE
                )
            )

        def place(chain: m.VGroup) -> None:
            joints = tips(clock.get_value())
            for k, (arrow, circle, shape) in enumerate(
                zip(arrows, circles, bases, strict=True)
            ):
                start, end = joints[k + 1], joints[k + 2]  # joint 1 is the fixed c₀
                turn = np.angle(end - start)
                rotation = np.array(
                    [
                        [np.cos(turn), -np.sin(turn), 0],
                        [np.sin(turn), np.cos(turn), 0],
                        [0, 0, 1],
                    ]
                )
                for part, base in zip(
                    arrow.family_members_with_points(), shape, strict=True
                ):
                    part.points = base @ rotation.T + to_point(start)
                circle.move_to(to_point(start))

        chain = m.VGroup(circles, arrows)
        chain.add_updater(place)
        place(chain)
        pen = m.Dot(radius=0.045, color=m.YELLOW)
        pen.add_updater(lambda dot: dot.move_to(to_point(tips(clock.get_value())[-1])))

        times = np.linspace(0, 1, 2400)
        curve = np.sum(
            c[None, :] * np.exp(m.TAU * 1j * np.outer(times, frequencies)), axis=1
        )
        full = m.VMobject(stroke_color=m.YELLOW, stroke_width=5).set_points_as_corners(
            to_point(curve)
        )
        drawn = full.copy()
        drawn.add_updater(
            lambda path: path.pointwise_become_partial(
                full, 0, min(clock.get_value(), 1)
            )
        )
        drawn.pointwise_become_partial(full, 0, 0)

        formula = m.MathTex(
            r"z(t) = \sum_{n=-50}^{50} c_n\, e^{2\pi i n t}", font_size=48
        ).to_edge(m.DOWN, buff=0.3)

        self.play(m.Write(letter), run_time=1.5)
        self.play(letter.animate.set_opacity(0.18), run_time=1)
        self.add(drawn)
        self.play(
            m.LaggedStart(*(m.GrowArrow(a) for a in arrows[:24]), lag_ratio=0.12),
            m.FadeIn(circles),
            m.FadeIn(arrows[24:]),
            run_time=2,
        )
        self.add(chain, pen)
        self.play(clock.animate.set_value(1.0), run_time=PERIOD, rate_func=m.linear)

        # a second lap, close up: the camera follows the pen
        clock.add_updater(lambda tracker, dt: tracker.increment_value(dt / PERIOD))
        close = m.ValueTracker(0.0)
        frame = self.camera.frame
        self.add(frame)  # a mobject's updaters run while it is in the scene

        def follow(view: m.Mobject) -> None:
            zoom = 1 / (1 - 0.78 * close.get_value())
            view.scale_to_fit_height(8 / zoom).move_to(
                close.get_value() * pen.get_center()
            )
            # strokes are as wide on screen at every zoom
            drawn.set_stroke(width=5 / zoom)
            circles.set_stroke(width=1.5 / zoom)
            for arrow in arrows:
                arrow.set_stroke(width=2.5 / zoom, family=False)
            pen.scale_to_fit_width(0.09 / zoom)

        frame.add_updater(follow)
        self.play(close.animate.set_value(1.0), run_time=1.5)
        self.wait(4)
        self.play(close.animate.set_value(0.0), run_time=1.5)
        frame.clear_updaters()
        clock.clear_updaters()
        chain.clear_updaters()
        drawn.clear_updaters()
        pen.clear_updaters()
        self.play(
            m.FadeOut(chain),
            m.FadeOut(pen),
            letter.animate.set_opacity(0),
            drawn.animate.set_fill(m.YELLOW, opacity=1),
            m.Write(formula),
            run_time=2,
        )
        self.wait(2)


if __name__ == "__main__":
    FourierPi().render("fourier_pi.mp4")
