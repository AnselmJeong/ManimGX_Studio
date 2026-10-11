# Source: manim/mobject/geometry/arc.py
import manimgx as m


class AnnularSectorExample(m.Scene):
    def construct(self):
        # Changes background color to clearly visualize changes in fill_opacity.
        self.camera.background_color = m.WHITE

        # The default parameter start_angle is 0, so the AnnularSector starts from the +x-axis.
        s1 = m.AnnularSector(color=m.YELLOW).move_to(2 * m.UL)

        # Different inner_radius and outer_radius than the default.
        s2 = m.AnnularSector(
            inner_radius=1.5, outer_radius=2, angle=45 * m.DEGREES, color=m.RED
        ).move_to(2 * m.UR)

        # fill_opacity is typically a number > 0 and <= 1. If fill_opacity=0, the AnnularSector is transparent.
        s3 = m.AnnularSector(
            inner_radius=1,
            outer_radius=1.5,
            angle=m.PI,
            fill_opacity=0.25,
            color=m.BLUE,
        ).move_to(2 * m.DL)

        # With a negative value for the angle, the AnnularSector is drawn clockwise from the start value.
        s4 = m.AnnularSector(
            inner_radius=1, outer_radius=1.5, angle=-3 * m.PI / 2, color=m.GREEN
        ).move_to(2 * m.DR)

        self.add(s1, s2, s3, s4)
        self.wait()
