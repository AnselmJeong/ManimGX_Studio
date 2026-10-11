# Source: manimgx API coverage (CE 0.21 `DecimalNumber.get_value`)
import manimgx as m


class DecimalGetValueExample(m.Scene):
    def construct(self):
        number = m.DecimalNumber(3.142, num_decimal_places=3).scale(1.5).shift(m.UP)
        bar = m.Rectangle(width=number.get_value(), height=0.5, fill_opacity=1)
        bar.next_to(number, m.DOWN)
        count = m.Integer(7).next_to(bar, m.DOWN)
        dots = m.VGroup(*(m.Dot() for _ in range(count.get_value()))).arrange(m.RIGHT)
        dots.next_to(count, m.DOWN)
        self.add(number, bar, count, dots)
        self.play(m.ChangeDecimalToValue(number, 2 * number.get_value()))
