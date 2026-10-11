# Source: example_scenes/basic.py
import manimgx as m


class UpdatersExample(m.Scene):
    def construct(self):
        decimal = m.DecimalNumber(
            0,
            show_ellipsis=True,
            num_decimal_places=3,
            include_sign=True,
        )
        square = m.Square().to_edge(m.UP)

        decimal.add_updater(lambda d: d.next_to(square, m.RIGHT))
        decimal.add_updater(lambda d: d.set_value(square.get_center()[1]))
        self.add(square, decimal)
        self.play(
            square.animate.to_edge(m.DOWN),
            rate_func=m.there_and_back,
            run_time=5,
        )
        self.wait()
