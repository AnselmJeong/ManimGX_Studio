import manimgx as m

NUM_KEYS = 14
KEY_WIDTH = 0.55
KEY_HEIGHT = 1.8
KEY_Y = -1.5
START_X = -(NUM_KEYS - 1) / 2 * KEY_WIDTH
KEY_TOP = KEY_Y + KEY_HEIGHT / 2


class TeacherScene(m.Scene):
    def construct(self) -> None:
        keys = m.VGroup(
            *[
                m.Rectangle(
                    width=KEY_WIDTH * 0.92,
                    height=KEY_HEIGHT,
                    color=m.WHITE,
                    fill_color=m.WHITE,
                    fill_opacity=0.92,
                    stroke_width=1.5,
                ).move_to([START_X + i * KEY_WIDTH, KEY_Y, 0])
                for i in range(NUM_KEYS)
            ]
        )
        self.play(
            m.LaggedStart(*[m.GrowFromCenter(k) for k in keys], lag_ratio=0.04),
            run_time=1.2,
        )
        self.wait(0.2)

        arc_radius = KEY_WIDTH / 2
        arcs = m.VGroup(
            *[
                m.Arc(
                    radius=arc_radius,
                    start_angle=0,
                    angle=m.PI,
                    color=m.WHITE,
                    stroke_width=2,
                ).move_to(
                    [START_X + (i + 0.5) * KEY_WIDTH, KEY_TOP + arc_radius / 2, 0]
                )
                for i in range(NUM_KEYS - 1)
            ]
        )
        self.play(m.Create(arcs, lag_ratio=0.08), run_time=1.4)
        self.wait(0.3)

        first_arc = arcs[0]
        twelfth_root = (
            m.MathTex("2^{1/12}")
            .scale(0.8)
            .next_to(
                first_arc,
                m.UP,
                buff=0.5,
            )
        )
        connector = m.Line(
            twelfth_root.get_bottom(),
            first_arc.get_top(),
            color=m.GREY,
            stroke_width=1.5,
        )
        self.play(m.Create(connector), m.Write(twelfth_root))
        self.wait(0.7)

        start_idx = 3
        span = 7
        highlighted = arcs[start_idx : start_idx + span]
        brace = m.Brace(
            m.VGroup(keys[start_idx], keys[start_idx + span]),
            m.DOWN,
            buff=0.25,
        )
        ratio_label = (
            m.MathTex(
                "2^{7/12} \\approx 1.498 \\approx \\tfrac{3}{2}",
            )
            .scale(0.9)
            .next_to(brace, m.DOWN, buff=0.2)
        )
        ratio_label.set_color(m.YELLOW)

        self.play(
            highlighted.animate.set_color(m.YELLOW).set_stroke(width=4),
            m.GrowFromCenter(brace),
            m.Write(ratio_label),
            run_time=1.4,
        )
        self.wait(2.0)
