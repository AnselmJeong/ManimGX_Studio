# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class SomeAnimations(m.Scene):
    def construct(self):
        square = m.Square()

        # some animations display mobjects, ...
        self.play(m.FadeIn(square))

        # ... some move or rotate mobjects around...
        self.play(m.Rotate(square, m.PI / 4))

        # some animations remove mobjects from the screen
        self.play(m.FadeOut(square))

        self.wait(1)
