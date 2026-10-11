# Source: manim/mobject/types/point_cloud_mobject.py
import manimgx as m


class PMobjectExample(m.Scene):
    def construct(self):

        pG = m.PGroup()  # This is just a collection of PMobject's

        # As the scale factor increases, the number of points
        # removed increases.
        for sf in range(1, 9 + 1):
            p = m.PointCloudDot(density=20, radius=1).thin_out(sf)
            # PointCloudDot is a type of PMobject
            # and can therefore be added to a PGroup
            pG.add(p)

        # This organizes all the shapes in a grid.
        pG.arrange_in_grid()

        self.add(pG)
        self.wait()
