# Source: docs/source/guides/using_text.rst
import manimgx as m


class Textt2cExample(m.Scene):
    def construct(self):
        t2cindices = m.Text("Hello", t2c={"[1:-1]": m.BLUE}).move_to(m.LEFT)
        t2cwords = m.Text("World", t2c={"rl": m.RED}).next_to(t2cindices, m.RIGHT)
        self.add(t2cindices, t2cwords)
        self.wait()
