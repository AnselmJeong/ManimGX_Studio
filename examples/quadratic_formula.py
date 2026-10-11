"""The quadratic formula, by completing a square.

ax² + bx + c = 0 is solved by making its left side a perfect square. Divide by a and move the
constant across: x² + (b/a)x is then the area of a square of side x and a rectangle b/a by x.
Cut the rectangle in two and fold one half under the square, and the shape is a square of side
x + b/2a missing one small corner, (b/2a)². Add that corner to both sides; the left side is now
(x + b/2a)², and a square root and a subtraction later, x = (−b ± √(b² − 4ac))/2a. Each term
keeps its color as it moves: the algebra is the picture.
"""

import numpy as np

import manimgx as m

WALL = 9.6  # the README wall's 5 seconds start here
SIZE = 60  # the equations' font size
X, HALF = 2.4, 0.8  # the picture's x and b/2a, in screen units
SQUARE, STRIP, CORNER = m.BLUE, m.TEAL, m.YELLOW
COLORS = {"x2": SQUARE, "bx": STRIP, "sq": CORNER, "sq2": CORNER}

Terms = list[tuple[str, str]]  # (key, LaTeX): a key names a term across the equations

E1: Terms = [("x2", "a x^2"), ("p1", "+"), ("bx", "b x"), ("p2", "+"), ("c", "c"),
             ("eq", "="), ("zero", "0")]  # fmt: skip
E2: Terms = [("x2", "x^2"), ("p1", "+"), ("bx", r"\frac{b}{a} x"), ("p2", "+"),
             ("c", r"\frac{c}{a}"), ("eq", "="), ("zero", "0")]  # fmt: skip
E3: Terms = [("x2", "x^2"), ("p1", "+"), ("bx", r"\frac{b}{a} x"), ("eq", "="),
             ("c", r"-\frac{c}{a}")]  # fmt: skip
E4: Terms = [("x2", "x^2"), ("p1", "+"), ("bx", r"\frac{b}{a} x"), ("p3", "+"),
             ("sq", r"\left( \frac{b}{2a} \right)^2"), ("eq", "="),
             ("sq2", r"\left( \frac{b}{2a} \right)^2"), ("c", r"-\frac{c}{a}")]  # fmt: skip
E5: Terms = [("lhs", r"\left( x + \frac{b}{2a} \right)^2"), ("eq", "="),
             ("rhs", r"\frac{b^2 - 4ac}{4a^2}")]  # fmt: skip
E6: Terms = [("x", "x"), ("plus", "+"), ("half", r"\frac{b}{2a}"), ("eq", "="),
             ("root", r"\pm \frac{ \sqrt{b^2 - 4ac} }{2a}")]  # fmt: skip
E7: Terms = [("x", "x"), ("eq", "="), ("sol", r"\frac{-b \pm \sqrt{b^2 - 4ac} }{2a}")]


class Equation(m.MathTex):
    """An equation whose terms are named, so that a step can say which becomes which."""

    def __init__(self, terms: Terms, font_size: float = SIZE) -> None:
        super().__init__(
            " ".join("{{ " + tex + " }}" for _, tex in terms), font_size=font_size
        )
        assert len(self.submobjects) == len(terms)
        self.parts = {
            key: part for (key, _), part in zip(terms, self.submobjects, strict=True)
        }
        for key, color in COLORS.items():
            if key in self.parts:
                self.parts[key].set_color(color)


def rectangle(
    left: float, top: float, width: float, height: float, color: str
) -> m.Rectangle:
    box = m.Rectangle(
        width=width, height=height, fill_color=color, fill_opacity=0.65,
        stroke_color=m.WHITE, stroke_width=2,
    )  # fmt: skip
    return box.move_to([left + width / 2, top - height / 2, 0])


class QuadraticFormula(m.Scene):
    def step(
        self,
        before: Equation,
        after: Equation,
        come_from: dict[str, m.Mobject] | None = None,
        path_arc: float = 0,
        run_time: float = 1.6,
    ) -> None:
        """Turn `before` into `after`. Symbols that appear in both fly to their new places
        and the rest fade; or, given `come_from`, each term moves to the term of the same key,
        and a term it names is drawn out of a copy of that mobject."""
        if come_from is None:
            self.play(
                m.TransformMatchingShapes(before, after, path_arc=path_arc),
                run_time=run_time,
            )
            return
        self.remove(before)
        self.add(*before.submobjects)
        moves: list[m.Animation] = []
        for key, part in after.parts.items():
            if key in come_from:
                moves.append(m.FadeTransform(come_from[key].copy(), part))
            elif key in before.parts:
                moves.append(m.ReplacementTransform(before.parts[key], part))
            else:
                moves.append(m.FadeIn(part, shift=0.25 * m.DOWN))
        moves += [
            m.FadeOut(part)
            for key, part in before.parts.items()
            if key not in after.parts
        ]
        self.play(*moves, run_time=run_time)
        self.remove(*before.submobjects, *after.submobjects)
        self.add(after)

    def construct(self) -> None:
        center, top = 0.4 * m.UP, 2.65 * m.UP
        e1, e2, e3 = (Equation(e).move_to(center) for e in (E1, E2, E3))
        e4, e5 = (Equation(e).move_to(top) for e in (E4, E5))
        e6 = Equation(E6).move_to(top)
        e7 = Equation(E7, font_size=76).move_to(0.2 * m.UP)

        self.play(m.Write(e1), run_time=1.5)
        self.wait(0.6)
        self.step(e1, e2)
        self.wait(0.4)
        self.step(e2, e3, path_arc=-0.5 * np.pi)
        self.wait(0.3)

        # the picture: x² + (b/a)x as areas, built from the terms
        left, ceiling = -(X + HALF) / 2, 0.75
        square = rectangle(left, ceiling, X, X, SQUARE)
        strip = rectangle(left + X, ceiling, 2 * HALF, X, STRIP)
        self.play(e3.animate.move_to(top), run_time=0.8)
        self.play(
            m.TransformFromCopy(e3.parts["x2"], square),
            m.TransformFromCopy(e3.parts["bx"], strip),
            run_time=1.4,
        )
        side = m.MathTex("x", font_size=44)
        x_top = side.copy().next_to(square, m.UP, buff=0.15)
        x_left = side.copy().next_to(square, m.LEFT, buff=0.15)
        b_over_a = m.MathTex(r"\frac{b}{a}", font_size=40, color=STRIP).next_to(
            strip, m.UP, 0.15
        )
        self.play(
            *(m.FadeIn(label) for label in (x_top, x_left, b_over_a)), run_time=0.7
        )

        # cut the strip in two and fold one half under the square
        kept = rectangle(left + X, ceiling, HALF, X, STRIP)
        folded = rectangle(left + X + HALF, ceiling, HALF, X, STRIP)
        self.remove(strip)
        self.add(kept, folded)
        half_top = m.MathTex(r"\frac{b}{2a}", font_size=36, color=STRIP)
        half_left = half_top.copy()
        under = rectangle(left, ceiling - X, X, HALF, STRIP)
        half_top.next_to(kept, m.UP, 0.15)
        half_left.next_to(under, m.LEFT, 0.15)
        self.play(
            m.Transform(folded, under, path_arc=-np.pi / 2),
            m.FadeTransform(b_over_a, half_top),
            m.FadeTransform(b_over_a.copy(), half_left),
            run_time=1.6,
        )
        corner = rectangle(left + X, ceiling - X, HALF, HALF, CORNER)
        outline = m.DashedVMobject(corner.copy().set_fill(opacity=0), num_dashes=16)
        self.play(m.Create(outline), run_time=0.6)
        self.play(m.FadeIn(corner), m.FadeOut(outline), run_time=0.5)

        # add the corner to both sides
        self.step(e3, e4, come_from={"sq": corner, "sq2": corner}, run_time=1.8)
        self.wait(0.5)

        # the left side is a square
        whole = m.Square(side_length=X + HALF, stroke_color=m.WHITE, stroke_width=6)
        whole.move_to([left + (X + HALF) / 2, ceiling - (X + HALF) / 2, 0])
        brace = m.Brace(whole, m.RIGHT, buff=0.15)
        brace_label = m.MathTex(r"x + \frac{b}{2a}", font_size=44).next_to(
            brace, m.RIGHT, 0.15
        )
        self.step(e4, e5, run_time=2)
        self.play(
            m.Create(whole), m.GrowFromCenter(brace), m.Write(brace_label), run_time=1.2
        )
        self.wait(0.8)

        # a square root, and x alone
        picture = m.VGroup(
            square, kept, folded, corner, whole, brace, brace_label,
            x_top, x_left, half_top, half_left,
        )  # fmt: skip
        self.play(m.FadeOut(picture), run_time=0.8)
        self.step(e5, e6, run_time=1.8)
        self.wait(0.3)
        self.step(e6, e7, run_time=1.8)
        box = m.SurroundingRectangle(e7, color=m.YELLOW, buff=0.35, stroke_width=5)
        self.play(m.Create(box), run_time=1)
        self.wait(2)


if __name__ == "__main__":
    QuadraticFormula().render("quadratic_formula.mp4")
