"""a² + b² = c², by moving four triangles.

Put four copies of a right triangle, with legs a and b and hypotenuse c, inside a square of
side a + b, each in a corner and turned a quarter turn from the last: the space they leave is a
tilted square on the hypotenuse, of area c². Now slide three of them, without turning, until
the four pair up into two rectangles: the space left is a square of side a and a square of side
b. The big square and the four triangles never changed, so neither did the space they leave:
a² + b² = c².
"""

import numpy as np

import manimgx as m

A, B = 2.4, 3.6  # the legs, in scene units
S = A + B  # the big square's side
CORNER = np.array([-5.75, -3.0, 0.0])  # the big square's lower left corner
CENTER = CORNER + np.array([S / 2, S / 2, 0.0])
A_COLOR, B_COLOR, C_COLOR = m.TEAL, m.GOLD, m.RED
TRIANGLE_FILL = m.BLUE_E
EDGE = 6  # the triangles' edges, in hundredths of a unit
OPACITY = 0.65  # the fill of the space left
WALL = 9.2


def at(x: float, y: float) -> np.ndarray:
    """The point (x, y) of the big square, measured from its lower left corner."""
    return CORNER + np.array([x, y, 0.0])


def triangle(right: np.ndarray, a_end: np.ndarray, b_end: np.ndarray) -> m.VGroup:
    """A right triangle with its right angle at `right` and its legs a and b ending at
    `a_end` and `b_end`: its body, its edges a, b and c, each in its color, and the mark
    of its right angle."""
    body = m.Polygon(right, a_end, b_end, stroke_width=0)
    body.set_fill(TRIANGLE_FILL, opacity=1.0)
    along_a, along_b = m.normalize(a_end - right), m.normalize(b_end - right)
    mark = m.VMobject(stroke_color=m.GREY_A, stroke_width=3)
    size = 0.3
    mark.set_points_as_corners(
        [
            right + size * along_a,
            right + size * (along_a + along_b),
            right + size * along_b,
        ]
    )
    return m.VGroup(
        body,
        m.Line(right, a_end, color=A_COLOR, stroke_width=EDGE),
        m.Line(right, b_end, color=B_COLOR, stroke_width=EDGE),
        m.Line(a_end, b_end, color=C_COLOR, stroke_width=EDGE),
        mark,
    )


def body(triangle: m.VGroup) -> m.VMobject:
    """A triangle's body: the region it covers."""
    shape = triangle[0]
    assert isinstance(shape, m.VMobject)
    return shape


def space_left(outline: m.VMobject, triangles: list[m.VGroup]) -> m.VMobject:
    """The part of the big square that the four triangles leave uncovered, as it is now."""
    covered = m.Union(*(body(t) for t in triangles))
    left = m.Difference(outline, covered, stroke_width=0)
    return left.set_fill(C_COLOR, opacity=OPACITY)


def label(
    tex: str, color: m.ManimColor, x: float, y: float, size: int = 60
) -> m.MathTex:
    return m.MathTex(tex, font_size=size, color=color).move_to(at(x, y))


class Pythagoras(m.Scene):
    def construct(self) -> None:
        outline = m.Polygon(at(0, 0), at(S, 0), at(S, S), at(0, S))
        outline.set_stroke(m.GREY_B, width=4)

        # one triangle in the lower right corner, then three copies, each turned a quarter
        # turn about the square's center from the last
        first = triangle(at(S, 0), at(S, A), at(A, 0))
        a_label = label("a", A_COLOR, S + 0.4, A / 2)
        b_label = label("b", B_COLOR, A + B / 2, -0.45)
        hypotenuse_mid = (at(S, A) + at(A, 0)) / 2
        c_label = m.MathTex("c", font_size=60, color=C_COLOR)
        c_label.move_to(hypotenuse_mid + 0.42 * m.normalize(CENTER - hypotenuse_mid))

        self.play(m.Create(outline), run_time=1.0)
        self.play(
            m.FadeIn(first[0]),
            *(m.Create(part) for part in first[1:]),
            run_time=1.2,
        )
        self.play(m.Write(a_label), m.Write(b_label), m.Write(c_label), run_time=0.8)
        triangles = [first]
        for _ in range(3):
            turned = triangles[-1].copy()
            self.play(m.Rotate(turned, m.PI / 2, about_point=CENTER), run_time=0.8)
            triangles.append(turned)
        _, upper_right, upper_left, lower_left = triangles

        # the other halves of the two labeled sides: each side is a + b
        self.play(
            m.FadeIn(label("a", A_COLOR, A / 2, -0.45)),
            m.FadeIn(label("b", B_COLOR, S + 0.4, A + B / 2)),
            run_time=0.6,
        )

        # the space left is the square on the hypotenuse
        tilted = m.Polygon(at(A, 0), at(S, A), at(B, S), at(0, B), stroke_width=0)
        tilted.set_fill(C_COLOR, opacity=OPACITY)
        c_squared = m.MathTex("c^2", font_size=96, color=C_COLOR).move_to(CENTER)
        self.add(tilted, *triangles)  # under the triangles' edges
        self.play(
            m.FadeIn(tilted), m.FadeOut(c_label), m.Write(c_squared), run_time=1.2
        )

        equation = m.MathTex("{{a^2}} + {{b^2}} = {{c^2}}", font_size=96)
        equation.move_to(np.array([4.0, 0.0, 0.0]))
        eq_a, plus, eq_b, equals, eq_c = equation
        eq_a.set_color(A_COLOR)
        eq_b.set_color(B_COLOR)
        eq_c.set_color(C_COLOR)
        self.play(m.TransformFromCopy(c_squared[0], eq_c), run_time=1.5)
        self.wait(0.5)

        # three slides, none turning: the space left flows around each triangle as it moves
        left = m.always_redraw(lambda: space_left(outline, triangles))
        self.remove(tilted)
        self.add(left, *triangles)
        slides = [
            (upper_left, at(A, -B) - at(0, 0)),  # across the tilted square, by c
            (upper_right, at(-B, 0) - at(0, 0)),  # left along the top, by b
            (lower_left, at(0, A) - at(0, 0)),  # up along the side, by a
        ]
        self.play(
            upper_left.animate(run_time=1.6).shift(slides[0][1]),
            m.FadeOut(c_squared, run_time=0.5),
        )
        for moving, by in slides[1:]:
            self.play(moving.animate.shift(by), run_time=1.6)

        # the space left is now two squares, on a and on b
        left.clear_updaters()
        a_square = m.Polygon(at(0, 0), at(A, 0), at(A, A), at(0, A), stroke_width=0)
        b_square = m.Polygon(at(A, A), at(S, A), at(S, S), at(A, S), stroke_width=0)
        for square in (a_square, b_square):
            square.set_fill(C_COLOR, opacity=OPACITY)
        self.remove(left)
        self.add(a_square, b_square, *triangles)
        a_squared = m.MathTex("a^2", font_size=80, color=A_COLOR).move_to(a_square)
        b_squared = m.MathTex("b^2", font_size=96, color=B_COLOR).move_to(b_square)
        self.play(
            a_square.animate.set_fill(A_COLOR, opacity=OPACITY),
            b_square.animate.set_fill(B_COLOR, opacity=OPACITY),
            m.Write(a_squared),
            m.Write(b_squared),
            run_time=1.2,
        )

        # the equation, from the areas' labels
        self.play(m.TransformFromCopy(a_squared[0], eq_a), m.FadeIn(plus), run_time=1.3)
        self.play(
            m.TransformFromCopy(b_squared[0], eq_b), m.FadeIn(equals), run_time=1.3
        )
        self.wait(2.0)


if __name__ == "__main__":
    Pythagoras().render("pythagoras.mp4")
