# Source: manim/animation/updaters/mobject_update_utils.py
import manimgx as m


class SpinningTriangle(m.Scene):
    def construct(self):
        tri = m.Triangle().set_fill(opacity=1).set_z_index(2)
        sq = m.Square().to_edge(m.LEFT)

        # will keep spinning while there is an animation going on
        m.always_rotate(tri, rate=2 * m.PI, about_point=m.ORIGIN)

        self.add(tri, sq)
        self.play(sq.animate.to_edge(m.RIGHT), rate_func=m.linear, run_time=1)
