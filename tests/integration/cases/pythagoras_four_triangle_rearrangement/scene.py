"""Prove the Pythagorean theorem by rearranging four right triangles inside a square."""

import numpy as np

import manimgx as m

# Leg lengths — must satisfy a + b = side length of the outer square.
A_LEG = 2.0
B_LEG = 3.0
SIDE = A_LEG + B_LEG  # 5.0


def _corner(x: float, y: float) -> np.ndarray:
    """Point on the big square whose interior spans [0, SIDE] x [0, SIDE], centered at origin."""
    half = SIDE / 2.0
    return np.array([x - half, y - half, 0.0])


def _triangle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, color: str) -> m.Polygon:
    return m.Polygon(p1, p2, p3).set_stroke(m.WHITE, 2).set_fill(color, 0.55)


class TeacherScene(m.Scene):
    def construct(self):
        # Bounding square — the arena where both arrangements live.
        outer = m.Square(side_length=SIDE).set_stroke(m.WHITE, 2).set_fill(m.BLACK, 0.0)

        # --- Arrangement A: two triangles along the bottom-left, two along the top-right.
        # The interior that remains has two squares of sides a and b in opposite corners.
        # Four right triangles:
        #   T1 = bottom-left: (0,0) - (a,0) - (a, b)
        #   T2 = top-left split: (a,0) - (a+b, 0) - (a, b)  [ actually, the canonical proof
        #        places triangles so the uncovered area forms an a^2 square and a b^2 square.
        #   Using the classic layout: place legs along the corners so interior = a^2 + b^2.
        tri_color = m.BLUE
        t1_a = _triangle(
            _corner(0, 0), _corner(B_LEG, 0), _corner(B_LEG, A_LEG), tri_color
        )
        t2_a = _triangle(
            _corner(B_LEG, 0), _corner(SIDE, 0), _corner(SIDE, B_LEG), tri_color
        )
        t3_a = _triangle(
            _corner(SIDE, B_LEG), _corner(SIDE, SIDE), _corner(A_LEG, SIDE), tri_color
        )
        t4_a = _triangle(
            _corner(A_LEG, SIDE), _corner(0, SIDE), _corner(0, B_LEG), tri_color
        )
        tris_a = m.VGroup(t1_a, t2_a, t3_a, t4_a)

        # Labels a^2 and b^2 in the two uncovered rectangles of arrangement A.
        # The uncovered area splits into two disjoint right-angled regions whose centers
        # can be computed by inspection of the triangle layout.
        label_a2 = m.MathTex("a^2", font_size=42).move_to(
            _corner(B_LEG + A_LEG / 2, A_LEG / 2)
        )
        label_b2 = m.MathTex("b^2", font_size=42).move_to(
            _corner(B_LEG / 2, B_LEG / 2 + A_LEG)
        )

        # --- Arrangement B: four triangles clustered around a single c^2 tilted square in the middle.
        # Canonical layout: triangles fill the four corners with their hypotenuses meeting to form
        # the tilted inner square of side c = sqrt(a^2 + b^2).
        t1_b = _triangle(_corner(0, 0), _corner(B_LEG, 0), _corner(0, A_LEG), tri_color)
        t2_b = _triangle(
            _corner(B_LEG, 0), _corner(SIDE, 0), _corner(SIDE, B_LEG), tri_color
        )
        t3_b = _triangle(
            _corner(SIDE, B_LEG), _corner(SIDE, SIDE), _corner(A_LEG, SIDE), tri_color
        )
        t4_b = _triangle(
            _corner(A_LEG, SIDE), _corner(0, SIDE), _corner(0, A_LEG), tri_color
        )
        m.VGroup(t1_b, t2_b, t3_b, t4_b)

        # c^2 label in the center — arrangement B exposes exactly a c^2 tilted square.
        label_c2 = m.MathTex("c^2", font_size=48).move_to(_corner(SIDE / 2, SIDE / 2))

        # Scene: show outer square + arrangement A + a^2/b^2 labels.
        self.play(m.Create(outer), run_time=0.8)
        self.play(m.FadeIn(tris_a), run_time=1.2)
        self.play(m.Write(label_a2), m.Write(label_b2), run_time=1.0)

        # Equation on the side.
        eq1 = m.MathTex("a^2 + b^2", font_size=40).to_edge(m.DOWN, buff=0.5)
        self.play(m.Write(eq1), run_time=0.8)

        # The rearrangement — Transform each triangle into its new position.
        # Use LaggedStart so the motion reads as a choreographed rearrangement.
        rearrange = m.LaggedStart(
            m.Transform(t1_a, t1_b, path_arc=45 * m.DEGREES),
            m.Transform(t2_a, t2_b, path_arc=45 * m.DEGREES),
            m.Transform(t3_a, t3_b, path_arc=45 * m.DEGREES),
            m.Transform(t4_a, t4_b, path_arc=45 * m.DEGREES),
            lag_ratio=0.2,
            run_time=2.4,
        )

        # Simultaneously fade out the a^2/b^2 labels; after the move the empty area
        # is the tilted c^2 square, so bring in c^2 via FadeTransform from label_a2.
        self.play(rearrange, m.FadeOut(label_b2), run_time=2.4)
        self.play(m.FadeTransform(label_a2, label_c2), run_time=0.9)

        # Close with the equation completion: a^2 + b^2  =  c^2.
        eq2 = m.MathTex("a^2 + b^2 = c^2", font_size=40).to_edge(m.DOWN, buff=0.5)
        self.play(m.FadeTransform(eq1, eq2), run_time=1.0)

        self.wait(0.5)
