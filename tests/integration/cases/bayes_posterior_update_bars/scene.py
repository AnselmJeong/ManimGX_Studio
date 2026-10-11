import manimgx as m

PRIOR = [0.33, 0.33, 0.34]
LIKELIHOOD = [0.8, 0.1, 0.1]


def make_bars(values, title_text: str, x_offset: float, color: str) -> m.VGroup:
    grp = m.VGroup()
    label = m.Tex(title_text, color=color).scale(0.6).move_to([x_offset, 2.5, 0])
    grp.add(label)
    for i, v in enumerate(values):
        bar = m.Rectangle(
            width=0.5,
            height=v * 4,
            color=color,
            fill_color=color,
            fill_opacity=0.65,
            stroke_width=1.5,
        ).move_to([x_offset - 0.7 + i * 0.7, v * 2 - 0.6, 0])
        grp.add(bar)
        grp.add(
            m.Tex(f"$H_{i + 1}$")
            .scale(0.5)
            .move_to([x_offset - 0.7 + i * 0.7, -0.9, 0]),
        )
    return grp


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Bayesian belief update").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        unnorm = [p * lk for p, lk in zip(PRIOR, LIKELIHOOD)]
        total = sum(unnorm)
        posterior = [u / total for u in unnorm]

        prior_bars = make_bars(PRIOR, "Prior", -4.5, m.BLUE)
        likely_bars = make_bars(LIKELIHOOD, "Likelihood", 0.0, m.GREEN)
        post_bars = make_bars(posterior, "Posterior", 4.5, m.YELLOW)

        self.play(m.FadeIn(prior_bars))
        self.play(m.FadeIn(likely_bars))
        self.play(m.FadeIn(post_bars))
        self.wait(2.0)
