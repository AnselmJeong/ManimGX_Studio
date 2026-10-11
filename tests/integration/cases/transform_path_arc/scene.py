# Source: manim/animation/transform.py
import manimgx as m


class TransformPathArc(m.Scene):
    def construct(self):
        def make_arc_path(start, end, arc_angle):
            points = []
            p_fn = m.path_along_arc(arc_angle)
            # alpha animates between 0.0 and 1.0, where 0.0
            # is the beginning of the animation and 1.0 is the end.
            for alpha in range(11):
                points.append(p_fn(start, end, alpha / 10.0))
            path = m.VMobject(stroke_color=m.YELLOW)
            path.set_points_smoothly(points)
            return path

        left = m.Circle(stroke_color=m.BLUE_E, fill_opacity=1.0, radius=0.5).move_to(
            m.LEFT * 2
        )
        colors = [m.TEAL_A, m.TEAL_B, m.TEAL_C, m.TEAL_D, m.TEAL_E, m.GREEN_A]
        # Positive angles move counter-clockwise, negative angles move clockwise.
        examples = [-90, 0, 30, 90, 180, 270]
        anims = []
        for idx, angle in enumerate(examples):
            left_c = left.copy().shift((3 - idx) * m.UP)
            left_c.fill_color = colors[idx]
            right_c = left_c.copy().shift(4 * m.RIGHT)
            path_arc = make_arc_path(
                left_c.get_center(),
                right_c.get_center(),
                arc_angle=angle * m.DEGREES,
            )
            desc = m.Text(f"{examples[idx]}°").next_to(left_c, m.LEFT)
            # Make the circles in front of the text in front of the arcs.
            self.add(
                path_arc.set_z_index(1),
                desc.set_z_index(2),
                left_c.set_z_index(3),
            )
            anims.append(m.Transform(left_c, right_c, path_arc=angle * m.DEGREES))

        self.play(*anims, run_time=2)
        self.wait()
