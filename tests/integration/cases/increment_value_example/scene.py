# Source: manimgx API coverage (CE 0.21 `DecimalNumber.increment_value`)
import manimgx as m


class IncrementValueExample(m.Scene):
    def construct(self):
        counter = m.Integer(0).scale(3)
        self.add(counter)
        for _ in range(5):
            self.wait(0.2)
            counter.increment_value(1)
        self.wait(0.3)
