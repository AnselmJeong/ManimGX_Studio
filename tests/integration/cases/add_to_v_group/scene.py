# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class AddToVGroup(m.Scene):
    def construct(self):
        circle_red = m.Circle(color=m.RED)
        circle_green = m.Circle(color=m.GREEN)
        circle_blue = m.Circle(color=m.BLUE)
        circle_red.shift(m.LEFT)
        circle_blue.shift(m.RIGHT)
        gr = m.VGroup(circle_red, circle_green)
        gr2 = m.VGroup(circle_blue)  # Constructor uses add directly
        self.add(gr, gr2)
        self.wait()
        gr += gr2  # Add group to another
        self.play(
            gr.animate.shift(m.DOWN),
        )
        gr -= gr2  # Remove group
        self.play(  # Animate groups separately
            gr.animate.shift(m.LEFT),
            gr2.animate.shift(m.UP),
        )
        self.play(  # Animate groups without modification
            (gr + gr2).animate.shift(m.RIGHT)
        )
        self.play(  # Animate group without component
            (gr - circle_red).animate.shift(m.RIGHT)
        )
