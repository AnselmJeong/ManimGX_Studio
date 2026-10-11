# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class Count(m.ChangeDecimalToValue):
    def __init__(
        self, number: m.DecimalNumber, start: float, end: float, **kwargs
    ) -> None:
        number.set_value(start)
        super().__init__(number, end, **kwargs)


class CountingScene(m.Scene):
    def construct(self):
        # Create Decimal Number and add it to scene
        number = m.DecimalNumber().set_color(m.WHITE).scale(5)
        # Add an updater to keep the DecimalNumber centered as its value changes
        number.add_updater(lambda number: number.move_to(m.ORIGIN))

        self.add(number)

        self.wait()

        # Play the Count Animation to count from 0 to 100 in 4 seconds
        self.play(Count(number, 0, 100), run_time=4, rate_func=m.linear)

        self.wait()
