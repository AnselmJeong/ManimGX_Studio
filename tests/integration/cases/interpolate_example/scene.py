# Source: manim/mobject/mobject.py
import manimgx as m


class InterpolateExample(m.Scene):
    def construct(self):
        # No need for point alignment:
        dotL = m.Dot(color=m.DARK_GREY).to_edge(m.LEFT)
        dotR = m.Dot(color=m.YELLOW).scale(10).to_edge(m.RIGHT)
        dotMid1 = m.VMobject().interpolate(dotL, dotR, alpha=0.1)
        dotMid2 = m.VMobject().interpolate(dotL, dotR, alpha=0.25)
        dotMid3 = m.VMobject().interpolate(dotL, dotR, alpha=0.5)
        dotMid4 = m.VMobject().interpolate(dotL, dotR, alpha=0.75)
        dots = m.VGroup(dotL, dotR, dotMid1, dotMid2, dotMid3, dotMid4)

        # Needs point alignment:
        line = (
            m.VMobject(stroke_width=4, fill_opacity=0)
            .set_points_as_corners([m.ORIGIN, m.UP])
            .to_edge(m.LEFT)
        )
        sq = m.Square(color=m.RED, fill_opacity=1, stroke_color=m.BLUE).to_edge(m.RIGHT)
        line.align_points(sq)
        if len(line.points) != len(sq.points):
            start = line.points[0]
            end = line.points[-1]
            segment_count = len(sq.points) // 4
            line.points = [
                start + (end - start) * ((3 * segment + handle) / (3 * segment_count))
                for segment in range(segment_count)
                for handle in range(4)
            ]
        mid1 = m.VMobject().interpolate(line, sq, alpha=0.1)
        mid2 = m.VMobject().interpolate(line, sq, alpha=0.25)
        mid3 = m.VMobject().interpolate(line, sq, alpha=0.5)
        mid4 = m.VMobject().interpolate(line, sq, alpha=0.75)
        linesquares = m.VGroup(line, sq, mid1, mid2, mid3, mid4)

        self.add(m.VGroup(dots, linesquares).arrange(m.DOWN, buff=1))
        self.wait()
