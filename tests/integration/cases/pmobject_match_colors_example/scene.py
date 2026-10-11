# Source: manim/mobject/types/point_cloud_mobject.py
import manimgx as m


class PMobjectMatchColorsExample(m.Scene):
    def construct(self):
        source = m.PointCloudDot(radius=0.8, density=20, color=m.GREEN)
        target = m.PointCloudDot(radius=0.8, density=20, color=m.RED)
        target.match_colors(source)
        all_rgbas = target.get_all_rgbas()
        marker = m.Text(f"{len(all_rgbas)} pts").scale(0.6)
        m.Group(target, marker).arrange(m.DOWN, buff=0.5)
        self.add(target, marker)
        self.wait()
