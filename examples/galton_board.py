"""Randomness that adds up to a bell: the Galton board.

Every ball meets a peg in each of the board's rows and bounces left or right, at random, as
if by a coin toss. The bin it lands in counts how many times it went right, so a ball's bin is
a sum of coin tosses, and the number of balls in bin k follows the binomial distribution: of
the 2ⁿ ways down, C(n, k) end in bin k. A few balls make a ragged pile; many make a bell, the
normal curve with the binomial's mean n/2 and variance n/4 (de Moivre, 1733; Galton, 1889).
"""

import numpy as np

import manimgx as m

ROWS = 10  # rows of pegs; there are ROWS + 1 bins
BALLS = 480
DX, DY = 0.7, 0.34  # between pegs in a row, and between rows
TOP = 3.1  # the first peg's height
FLOOR = -3.75  # the bins' floor
PEG, BALL = 0.05, 0.06  # radii
GAP = 2.04 * BALL  # between the centers of two balls side by side in a pile
GRAVITY = 25.0  # scene units per second², in the board's own time
HOP = 0.26  # seconds from one peg to the next, in the board's own time
RELEASE = TOP + 0.62  # where balls are let go, in the funnel's neck
SEED = 7
WALL = 8.2


def peg(row: int, k: int) -> np.ndarray:
    """The k-th peg (from the left) of a row."""
    return np.array([(k - row / 2) * DX, TOP - row * DY, 0.0])


def pile(count: int) -> np.ndarray:
    """Where the balls of a bin come to rest, relative to its floor's middle: rows of five
    and of four in turn, packed, each row filled in a scattered order."""
    fives = np.array([0.0, -2.0, 2.0, -1.0, 1.0]) * GAP
    fours = np.array([-0.5, 1.5, 0.5, -1.5]) * GAP
    places = np.empty((count, 2))
    for s in range(count):
        pair, r = divmod(s, 9)
        layer, x = (2 * pair, fives[r]) if r < 5 else (2 * pair + 1, fours[r - 5])
        places[s] = [x, BALL + layer * GAP * np.sqrt(3) / 2]
    return places


def release_times() -> np.ndarray:
    """When each ball is let go, in board time: three alone, then faster and faster."""
    first = [0.0, 1.4, 2.8]
    times, s = list(first), 0.0
    while len(times) < BALLS:
        times.append(4.2 + s)
        s += 1 / min(2 + 9 * s**2, 70)  # balls per second, s seconds into the rush
    return np.array(times)


class Board:
    """Every ball's way down, worked out in advance: its release, its bounces, its rest."""

    def __init__(self, releases: np.ndarray, rng: np.random.Generator) -> None:
        count = len(releases)
        self.releases = releases
        rights = rng.integers(0, 2, size=(count, ROWS))  # 1: it bounced right
        self.bins = rights.sum(1)
        before = np.concatenate([np.zeros((count, 1), int), np.cumsum(rights, 1)], 1)
        rows = np.arange(ROWS)
        # where it touches the peg of each row: above its center, by the two radii
        self.contacts = np.stack(
            [
                (before[:, :ROWS] - rows / 2) * DX,
                np.broadcast_to(TOP - rows * DY + PEG + BALL, (count, ROWS)),
            ],
            -1,
        )
        self.fall = float(np.sqrt(2 * (RELEASE - self.contacts[0, 0, 1]) / GRAVITY))
        self.kick = (
            GRAVITY * HOP**2 / 2 - DY
        ) / HOP  # up, off a peg: each hop drops DY
        # it comes to rest in its bin on top of those that came before it
        rank = np.zeros(count, int)
        self.counts = np.zeros(ROWS + 1, int)
        for i in np.argsort(releases, kind="stable"):
            rank[i] = self.counts[self.bins[i]]
            self.counts[self.bins[i]] += 1
        places = pile(int(self.counts.max()))
        self.rest = places[rank] + np.column_stack(
            [(self.bins - ROWS / 2) * DX, np.full(count, FLOOR)]
        )
        drop = self.contacts[:, -1, 1] - self.rest[:, 1]
        self.last = (self.kick + np.sqrt(self.kick**2 + 2 * GRAVITY * drop)) / GRAVITY
        self.landed = releases + self.fall + (ROWS - 1) * HOP + self.last

    def positions(self, t: float) -> np.ndarray:
        """Where the balls let go by board time t are then, as rows (x, y, 0)."""
        shown = self.releases <= t
        u = t - self.releases[shown]
        contacts, rest, last = self.contacts[shown], self.rest[shown], self.last[shown]
        xy = np.empty((len(u), 2))
        # falling onto the first peg
        a = u < self.fall
        xy[a, 0] = contacts[a, 0, 0]
        xy[a, 1] = RELEASE - GRAVITY * u[a] ** 2 / 2
        # hopping from peg to peg
        bouncing = u - self.fall
        h = (bouncing >= 0) & (bouncing < (ROWS - 1) * HOP)
        hop = np.minimum((bouncing[h] // HOP).astype(int), ROWS - 2)
        w = bouncing[h] - hop * HOP
        here, there = contacts[h, hop], contacts[h, hop + 1]
        xy[h, 0] = here[:, 0] + (there[:, 0] - here[:, 0]) * w / HOP
        xy[h, 1] = here[:, 1] + self.kick * w - GRAVITY * w**2 / 2
        # the last bounce, into the bin, onto the pile
        f = bouncing >= (ROWS - 1) * HOP
        w = np.minimum(bouncing[f] - (ROWS - 1) * HOP, last[f])
        here = contacts[f, -1]
        xy[f, 0] = here[:, 0] + (rest[f, 0] - here[:, 0]) * w / last[f]
        flying = here[:, 1] + self.kick * w - GRAVITY * w**2 / 2
        xy[f, 1] = np.where(w >= last[f], rest[f, 1], flying)
        return np.column_stack([xy, np.zeros(len(u))])


class GaltonBoard(m.Scene):
    def construct(self) -> None:
        board = Board(release_times(), np.random.default_rng(SEED))

        pegs = m.VGroup(
            *(
                m.Dot(peg(r, k), radius=PEG, color=m.GREY_B)
                for r in range(ROWS)
                for k in range(r + 1)
            )
        )
        wall_top = TOP - (ROWS - 1) * DY - 0.45
        edges = (np.arange(ROWS + 2) - (ROWS + 1) / 2) * DX
        bins = m.VGroup(
            m.Line([edges[0], FLOOR, 0], [edges[-1], FLOOR, 0]),
            *(m.Line([x, FLOOR, 0], [x, wall_top, 0]) for x in edges),
        ).set_stroke(m.GREY_B, width=3)

        funnel = m.VGroup(
            m.Line([-0.5, RELEASE + 0.22, 0], [-0.1, RELEASE - 0.05, 0]),
            m.Line([0.5, RELEASE + 0.22, 0], [0.1, RELEASE - 0.05, 0]),
        ).set_stroke(m.GREY_B, width=3)

        clock = m.ValueTracker(0.0)  # the board's own time
        balls = m.PMobject(stroke_width=200 * BALL)
        blue = m.BLUE.to_rgba()

        def place(cloud: m.Mobject) -> None:
            points = board.positions(clock.get_value())
            cloud.points = points
            cloud.paint = cloud.paint.but(fill=np.tile(blue, (len(points), 1)))

        balls.add_updater(place)
        place(balls)

        landed = m.Integer(0, font_size=56)
        landed_row = m.VGroup(m.Tex("balls", font_size=44), landed)
        landed_row.arrange(m.RIGHT, buff=0.3).to_corner(m.UL)
        landed.add_updater(
            lambda d: d.set_value(int(np.sum(board.landed <= clock.get_value())))
        )

        self.add(balls)
        self.play(
            m.LaggedStart(*(m.FadeIn(p, scale=0.5) for p in pegs), lag_ratio=0.02),
            m.Create(bins),
            m.Create(funnel),
            m.FadeIn(landed_row),
            run_time=1.2,
        )

        # the board's clock against the film's: 0.8 of life while three balls fall alone,
        # then speeding up to twice life as the rest pour in
        end = float(board.landed.max()) + 0.2
        film = np.linspace(0, 30, 3001)
        speed = np.interp(film, [0, 5.0, 8.0], [0.8, 0.8, 2.0])
        board_time = np.concatenate(
            [[0], np.cumsum((speed[1:] + speed[:-1]) / 2 * np.diff(film))]
        )
        seconds = float(np.interp(end, board_time, film))

        def pace(alpha: float) -> float:
            return float(np.interp(alpha * seconds, film, board_time)) / end

        self.play(clock.animate.set_value(end), run_time=seconds, rate_func=pace)

        # the bell: the normal curve with the binomial's mean and variance, over the bins
        mean, variance = ROWS / 2, ROWS / 4
        per_ball = GAP * np.sqrt(3) / 9  # a pile's height, per ball in it

        def bell(x: float) -> float:
            k = x / DX + ROWS / 2  # x, in bins
            density = np.exp(-((k - mean) ** 2) / (2 * variance)) / np.sqrt(
                2 * np.pi * variance
            )
            return FLOOR + BALLS * density * per_ball

        curve = m.FunctionGraph(bell, x_range=[edges[0], edges[-1]], color=m.YELLOW)
        curve.set_stroke(width=6)
        label = m.VGroup(
            m.MathTex(rf"\mu = {mean:g}", font_size=52),
            m.MathTex(rf"\sigma^2 = {variance:g}", font_size=52),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        label.set_color(m.YELLOW).move_to(np.array([edges[-1] + 1.6, FLOOR + 2.2, 0.0]))
        self.play(m.Create(curve), m.FadeIn(label), run_time=2.0)
        self.wait(2.0)


if __name__ == "__main__":
    GaltonBoard().render("galton_board.mp4")
