"""A curve that fills a square: Hilbert's.

Split a square into a 2ⁿ × 2ⁿ grid and run a path through the centers of all its cells,
Hilbert's way: the path of order n + 1 is the path of order n with every point replaced by a
small copy of the first one, a U through the four quarters of its cell, turned so that the U's
join up. Each order doubles the length and halves the gaps, while every point of the path moves
less and less: the paths converge, to a curve that passes through every point of the square
(Hilbert, 1891). Its colors run along its length, so each part of the square keeps its color.
"""

import numpy as np

import manimgx as m

SIDE = 7.2  # the square's side, in scene units
CENTER = np.array([-1.5, 0.0, 0.0])
LAST_ORDER = 7
PIECES = 256  # the most pieces a path is drawn in, each in its own color
COLORS = [m.BLUE, m.TEAL, m.GREEN, m.YELLOW, m.GOLD, m.RED, m.MAROON, m.PURPLE]
WALL = 4.4


def hilbert(order: int) -> np.ndarray:
    """The cells (x, y) of the 2^order × 2^order grid, in the order the path visits them."""
    size = 2**order
    t = np.arange(size * size)
    x, y = np.zeros_like(t), np.zeros_like(t)
    s = 1
    while s < size:
        rx = (t // 2) & 1
        ry = (t ^ rx) & 1
        swap = ry == 0
        flip = swap & (rx == 1)
        x, y = np.where(flip, s - 1 - x, x), np.where(flip, s - 1 - y, y)
        x, y = np.where(swap, y, x), np.where(swap, x, y)
        x, y = x + s * rx, y + s * ry
        t, s = t // 4, 2 * s
    return np.stack([x, y], 1)


def vertices(order: int) -> np.ndarray:
    """The path of the given order: the centers of its cells, on screen."""
    cell = SIDE / 2**order
    corner = CENTER - SIDE / 2 * (m.RIGHT + m.UP)
    xy = (hilbert(order) + 0.5) * cell
    return corner + np.column_stack([xy, np.zeros(len(xy))])


def pieces(count: int) -> list[np.ndarray]:
    """The vertices of each piece of a path through `count` vertices: its segments, or, for
    a long path, PIECES runs of them, each ending where the next begins."""
    if count <= PIECES:
        return [np.array([k, k + 1]) for k in range(count - 1)]
    run = count // PIECES
    return [np.arange(k * run, min((k + 1) * run + 1, count)) for k in range(PIECES)]


def rainbow(s: float) -> m.ManimColor:
    """The color a fraction s of the way along the path."""
    x = s * (len(COLORS) - 1)
    k = min(int(x), len(COLORS) - 2)
    return m.interpolate_color(COLORS[k], COLORS[k + 1], x - k)


def width(order: int) -> float:
    """The stroke for a path of this order: four tenths of its cell, at most 12."""
    return min(12.0, 40 * SIDE / 2**order)


def drawn(
    points: np.ndarray, runs: list[np.ndarray], places: np.ndarray, order: int
) -> m.VGroup:
    """A path drawn piece by piece: piece k through points[runs[k]], colored by where along
    the path its vertices are (places: a fraction of the way, per point)."""
    group = m.VGroup()
    for run in runs:
        piece = m.VMobject(
            stroke_width=width(order), stroke_color=rainbow(places[run].mean())
        )
        piece.set_points_as_corners(points[run])
        piece.cap_style = m.CapStyleType.ROUND
        piece.joint_type = m.LineJointType.ROUND
        group.add(piece)
    return group


def path_length(points: np.ndarray) -> float:
    """The length of the path through the points, in sides of the square."""
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum() / SIDE)


class HilbertCurve(m.Scene):
    def construct(self) -> None:
        outline = m.Square(SIDE).move_to(CENTER)
        outline.set_stroke(m.GREY_C, width=2, opacity=0.6)

        first = vertices(1)
        path = drawn(first, pieces(4), np.arange(4) / 3, 1)

        order_label = m.Tex("order", font_size=48)
        order_value = m.Integer(1, font_size=72)
        length_label = m.Tex("length", font_size=48)
        length_value = m.DecimalNumber(
            path_length(first), num_decimal_places=2, font_size=72
        )
        column = m.VGroup(
            m.VGroup(order_label, order_value).arrange(m.RIGHT, buff=0.3),
            m.VGroup(length_label, length_value).arrange(m.RIGHT, buff=0.3),
        )
        column.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.6).move_to(
            np.array([4.3, 0.0, 0.0])
        )
        side_note = m.Tex("(in sides of the square)", font_size=32, color=m.GREY_B)
        side_note.next_to(column, m.DOWN, aligned_edge=m.LEFT, buff=0.3)

        self.play(
            m.Create(outline),
            m.Create(path, lag_ratio=1.0),
            m.FadeIn(column),
            m.FadeIn(side_note),
            run_time=1.6,
        )
        self.wait(0.6)

        for order in range(1, LAST_ORDER):
            parents = vertices(order)
            children = vertices(order + 1)
            count = len(children)
            parent_of = np.arange(count) // 4
            runs = pieces(count)
            before = drawn(
                parents[parent_of], runs, parent_of / (len(parents) - 1), order
            )
            after = drawn(children, runs, np.arange(count) / (count - 1), order + 1)

            def measure(
                d: m.Mobject,
                alpha: float,
                start: np.ndarray = parents[parent_of],
                end: np.ndarray = children,
            ) -> None:
                assert isinstance(d, m.DecimalNumber)
                d.set_value(path_length((1 - alpha) * start + alpha * end))
                d.next_to(length_label, m.RIGHT, buff=0.3)

            self.remove(path)
            self.add(before)
            order_value.set_value(order + 1)
            self.play(
                m.Transform(before, after),
                m.UpdateFromAlphaFunc(length_value, measure),
                run_time=2.2,
            )
            self.remove(before)
            self.add(after)
            path = after
        self.wait(2.0)


if __name__ == "__main__":
    HilbertCurve().render("hilbert_curve.mp4")
