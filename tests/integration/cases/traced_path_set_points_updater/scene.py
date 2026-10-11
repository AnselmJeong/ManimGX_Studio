# Regression: a complete Printery scene rendered under Manim CE 0.20.1 but
# failed under manimgx when one TracedPath mirrored another with set_points().
import manimgx as m


class TracedPathSetPointsUpdater(m.Scene):
    def construct(self) -> None:
        dot = m.Dot(m.LEFT * 2)
        trail = m.TracedPath(dot.get_center, stroke_color=m.BLUE)
        glow = m.TracedPath(dot.get_center, stroke_color=m.WHITE, stroke_width=8)
        glow.add_updater(
            lambda path: path.set_points(trail.get_points()),
        )
        self.add(trail, glow, dot)
        self.play(dot.animate.shift(m.RIGHT * 4), run_time=1)
        self.wait(0.2)
