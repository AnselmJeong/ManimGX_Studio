# Source: manim/mobject/geometry/tips.py
import manimgx as m


class ArrowTipsShowcase(m.Scene):
    def construct(self):
        tip_names = [
            "Default (YELLOW)",
            "ArrowTriangleTip",
            "Default",
            "ArrowSquareTip",
            "ArrowSquareFilledTip",
            "ArrowCircleTip",
            "ArrowCircleFilledTip",
            "StealthTip",
        ]

        big_arrows = [
            m.Arrow(start=[-4, 3.5, 0], end=[2, 3.5, 0], color=m.YELLOW),
            m.Arrow(start=[-4, 2.5, 0], end=[2, 2.5, 0], tip_shape=m.ArrowTriangleTip),
            m.Arrow(start=[-4, 1.5, 0], end=[2, 1.5, 0]),
            m.Arrow(start=[-4, 0.5, 0], end=[2, 0.5, 0], tip_shape=m.ArrowSquareTip),
            m.Arrow([-4, -0.5, 0], [2, -0.5, 0], tip_shape=m.ArrowSquareFilledTip),
            m.Arrow([-4, -1.5, 0], [2, -1.5, 0], tip_shape=m.ArrowCircleTip),
            m.Arrow([-4, -2.5, 0], [2, -2.5, 0], tip_shape=m.ArrowCircleFilledTip),
            m.Arrow([-4, -3.5, 0], [2, -3.5, 0], tip_shape=m.StealthTip),
        ]

        small_arrows = (
            arrow.copy().scale(0.5, scale_tips=True).next_to(arrow, m.RIGHT)
            for arrow in big_arrows
        )

        labels = (
            m.Text(tip_names[i], font="monospace", font_size=20, color=m.BLUE).next_to(
                big_arrows[i], m.LEFT
            )
            for i in range(len(big_arrows))
        )

        self.add(*big_arrows, *small_arrows, *labels)
        self.wait()
