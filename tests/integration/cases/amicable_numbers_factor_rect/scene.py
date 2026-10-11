import manimgx as m

DIVISORS_220 = [1, 2, 4, 5, 10, 11, 20, 22, 44, 55, 110]
DIVISORS_284 = [1, 2, 4, 71, 142]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Amicable pair: 220 and 284").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        left_label = (
            m.Tex("220 $\\to$ proper divisors").scale(0.65).move_to([-3.5, 2.5, 0])
        )
        left_eq = (
            m.Tex(
                f"sum = {sum(DIVISORS_220)} = 284",
                color=m.YELLOW,
            )
            .scale(0.6)
            .move_to([-3.5, 1.6, 0])
        )
        right_label = (
            m.Tex("284 $\\to$ proper divisors").scale(0.65).move_to([3.5, 2.5, 0])
        )
        right_eq = (
            m.Tex(
                f"sum = {sum(DIVISORS_284)} = 220",
                color=m.YELLOW,
            )
            .scale(0.6)
            .move_to([3.5, 1.6, 0])
        )

        self.play(m.Write(left_label), m.Write(right_label))
        self.play(m.Write(left_eq), m.Write(right_eq))

        left_divs = (
            m.Tex(", ".join(str(d) for d in DIVISORS_220))
            .scale(0.55)
            .move_to(
                [-3.5, -0.3, 0],
            )
        )
        right_divs = (
            m.Tex(", ".join(str(d) for d in DIVISORS_284))
            .scale(0.55)
            .move_to(
                [3.5, -0.3, 0],
            )
        )
        self.play(m.Write(left_divs), m.Write(right_divs))

        caption = (
            m.Tex(
                "Each is the sum of the other's proper divisors",
            )
            .scale(0.7)
            .to_edge(m.DOWN, buff=0.6)
        )
        self.play(m.Write(caption))
        self.wait(2.0)
