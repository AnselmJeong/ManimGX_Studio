# Source: example_scenes/basic.py
import numpy as np

import manimgx as m


class OpeningManim(m.Scene):
    def construct(self):
        title = m.Tex(r"This is some \LaTeX")
        basel = m.Tex(r"$\sum_{n=1}^\infty \frac{1}{n^2} = \frac{\pi^2}{6}$")
        m.VGroup(title, basel).arrange(m.DOWN)
        self.play(
            m.Write(title),
            m.FadeIn(basel, shift=m.DOWN),
        )
        self.wait()

        transform_title = m.Tex("That was a transform")
        transform_title.to_corner(m.UP + m.LEFT)
        self.play(
            m.Transform(title, transform_title),
            m.LaggedStart(*(m.FadeOut(obj, shift=m.DOWN) for obj in basel)),
        )
        self.wait()

        grid = m.NumberPlane()
        grid_title = m.Tex("This is a grid", font_size=72)
        grid_title.move_to(transform_title)

        self.add(grid, grid_title)  # Make sure title is on top of grid
        self.play(
            m.FadeOut(title),
            m.FadeIn(grid_title, shift=m.UP),
            m.Create(grid, run_time=3, lag_ratio=0.1),
        )
        self.wait()

        grid_transform_title = m.Tex(
            r"That was a non-linear function \\ applied to the grid",
        )
        grid_transform_title.move_to(grid_title, m.UL)
        grid.prepare_for_nonlinear_transform()
        self.play(
            m.ApplyPointwiseFunction(
                lambda p: (
                    p
                    + np.array(
                        [
                            np.sin(p[1]),
                            np.sin(p[0]),
                            0,
                        ],
                    )
                ),
                grid,
            ),
            run_time=3,
        )
        self.wait()
        self.play(m.Transform(grid_title, grid_transform_title))
        self.wait()
