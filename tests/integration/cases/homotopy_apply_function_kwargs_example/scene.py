# Source: manim/animation/movement.py
import manimgx as m


class HomotopyApplyFunctionKwargsExample(m.Scene):
    def construct(self):
        square = m.Square().shift(m.RIGHT * 2)
        self.add(square)

        def shrink_to_origin(x, y, z, t):
            return (x * (1.0 - 0.5 * t), y * (1.0 - 0.5 * t), z)

        self.play(
            m.Homotopy(
                shrink_to_origin,
                square,
                apply_function_kwargs={"about_point": [2.0, 0.0, 0.0]},
                run_time=1.0,
            )
        )
