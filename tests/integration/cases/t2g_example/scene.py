# Source: docs/source/guides/using_text.rst
import manimgx as m


class t2gExample(m.Scene):
    def construct(self):
        t2gindices = m.Text(
            "Hello",
            t2g={
                "[1:-1]": (m.RED, m.GREEN),
            },
        ).move_to(m.LEFT)
        t2gwords = m.Text(
            "World",
            t2g={
                "World": (m.RED, m.BLUE),
            },
        ).next_to(t2gindices, m.RIGHT)
        self.add(t2gindices, t2gwords)
        self.wait()
