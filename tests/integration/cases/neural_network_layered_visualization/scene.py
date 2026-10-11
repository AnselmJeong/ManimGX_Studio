import manimgx as m

LAYER_SIZES = [4, 6, 6, 2]
LAYER_X = [-4.5, -1.5, 1.5, 4.5]
NEURON_R = 0.18
SPACING = 0.7


class TeacherScene(m.Scene):
    def construct(self) -> None:
        neurons: list[m.VGroup] = []
        for i, n in enumerate(LAYER_SIZES):
            ys = [(j - (n - 1) / 2) * SPACING for j in range(n)]
            layer = m.VGroup(
                *[
                    m.Circle(
                        radius=NEURON_R,
                        color=m.WHITE,
                        fill_color=m.BLACK,
                        fill_opacity=1.0,
                    ).move_to([LAYER_X[i], y, 0])
                    for y in ys
                ]
            )
            neurons.append(layer)

        connections = m.VGroup()
        for i in range(len(LAYER_SIZES) - 1):
            for a in neurons[i]:
                for b in neurons[i + 1]:
                    connections.add(
                        m.Line(
                            a.get_center(),
                            b.get_center(),
                            color=m.GREY,
                            stroke_width=1,
                        )
                    )

        self.play(m.Create(connections, lag_ratio=0.002), run_time=1.5)
        for layer in neurons:
            self.play(
                m.LaggedStart(*[m.FadeIn(n) for n in layer], lag_ratio=0.06),
                run_time=0.4,
            )

        for layer in neurons:
            self.play(layer.animate.set_fill(m.YELLOW, opacity=1.0), run_time=0.5)
            self.wait(0.15)

        title = m.Tex("Feed-forward neural network").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))
        self.wait(1.5)
