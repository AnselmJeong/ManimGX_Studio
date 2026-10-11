"""Show how to find the path of a ball bouncing once off the right wall of a pool table by unfolding the table reflection."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Tests the 'reflection unfold' idiom: rotate the table by pi about the UP axis "
    "through the right-wall midpoint so the reflected copy appears to the right, "
    "then Transform the straight A-to-B' line into the actual bounce path."
)


class TeacherScene(m.Scene):
    def construct(self):
        # Real table — left-half of the frame.
        table_w, table_h = 4.0, 3.0
        table_cx = -2.5  # center x of the real table
        table_cy = 0.0

        table = (
            m.Rectangle(
                width=table_w,
                height=table_h,
                color=m.GREEN_E,
            )
            .set_fill(m.GREEN_E, 0.35)
            .set_stroke(m.WHITE, 2.5)
        )
        table.move_to(np.array([table_cx, table_cy, 0.0]))

        # Anchor points.
        left_x = table_cx - table_w / 2.0
        right_x = table_cx + table_w / 2.0
        table_cy - table_h / 2.0
        top_y = table_cy + table_h / 2.0

        A = np.array([left_x + 0.6, table_cy - 0.4, 0.0])  # ball
        B = np.array([right_x - 0.3, top_y - 0.3, 0.0])  # pocket in real table
        right_wall_mid = np.array([right_x, table_cy, 0.0])

        # Bounce point (computed by the unfolding trick):
        # In the reflected table, B is at B' = (2*right_x - B.x, B.y). The straight line
        # A -> B' crosses x = right_x at the bounce point.
        B_prime = np.array([2.0 * right_x - B[0], B[1], 0.0])
        t = (right_x - A[0]) / (B_prime[0] - A[0])
        bounce_point = A + t * (B_prime - A)

        ball = m.Dot(A, radius=0.12, color=m.YELLOW)
        ball_label = (
            m.MathTex("A", color=m.YELLOW).scale(0.7).next_to(ball, m.DL, buff=0.08)
        )
        pocket = m.Dot(B, radius=0.12, color=m.RED)
        pocket_label = (
            m.MathTex("B", color=m.RED).scale(0.7).next_to(pocket, m.UR, buff=0.08)
        )

        self.play(m.Create(table), run_time=0.9)
        self.play(
            m.FadeIn(ball),
            m.Write(ball_label),
            m.FadeIn(pocket),
            m.Write(pocket_label),
            run_time=0.8,
        )

        # Draw the actual bounce path A -> bounce_point -> B.
        bounce_path = m.VMobject()
        bounce_path.set_points_as_corners([A, bounce_point, B])
        bounce_path.set_stroke(m.YELLOW, width=4.0)
        self.play(m.Create(bounce_path), run_time=1.5)

        # Now unfold: create a reflected copy of the table across the right wall.
        # Rotate by pi about the UP axis passing through right_wall_mid:
        #   (x, y, 0) -> (2*right_x - x, y, 0)
        reflected_table = (
            table.copy().set_stroke(m.WHITE, 2.0, opacity=0.8).set_fill(m.GREEN_E, 0.15)
        )
        reflected_pocket = m.Dot(B, radius=0.12, color=m.RED).set_opacity(0.9)
        reflected_pocket_label = m.MathTex("B'", color=m.RED).scale(0.7)

        # Drop them into the scene at the original position; Rotate will unfold them.
        self.add(reflected_table, reflected_pocket)

        # Unfold via Rotate about UP through right_wall_mid.
        self.play(
            m.Rotate(
                reflected_table,
                m.PI,
                axis=m.UP,
                about_point=right_wall_mid,
            ),
            m.Rotate(
                reflected_pocket,
                m.PI,
                axis=m.UP,
                about_point=right_wall_mid,
            ),
            run_time=1.8,
        )
        # After the rotation, the pocket mobject is at B_prime; label it.
        reflected_pocket_label.next_to(reflected_pocket, m.UR, buff=0.08)
        self.play(m.Write(reflected_pocket_label), run_time=0.6)

        # Draw the STRAIGHT line from A to B' — the shortest "unfolded" path.
        straight_line = m.Line(A, B_prime, color=m.TEAL, stroke_width=4.0)
        self.play(m.Create(straight_line), run_time=1.2)

        # Highlight the bounce point on the right wall.
        bounce_marker = m.Dot(bounce_point, radius=0.09, color=m.WHITE)
        self.play(m.FadeIn(bounce_marker, scale=1.5), run_time=0.6)

        # Morph the straight line into the zig-zag bounce path, showing equivalence.
        straight_as_path = m.VMobject()
        straight_as_path.set_points_as_corners([A, bounce_point, B_prime])
        straight_as_path.set_stroke(m.TEAL, width=4.0)

        target_path = m.VMobject()
        target_path.set_points_as_corners([A, bounce_point, B])
        target_path.set_stroke(m.TEAL, width=4.0)

        self.play(m.Transform(straight_line, straight_as_path), run_time=0.4)
        self.play(m.Transform(straight_line, target_path), run_time=1.5)

        self.wait(0.5)
