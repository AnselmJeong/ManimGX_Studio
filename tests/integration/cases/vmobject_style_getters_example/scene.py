# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VMobjectStyleGettersExample(m.Scene):
    def construct(self):
        styled = m.Square(side_length=1.5)
        styled.set_fill(m.PURPLE, opacity=0.7)
        styled.set_stroke(m.YELLOW, width=6)

        mirror = m.Circle(radius=0.8)
        mirror.match_style(styled)

        fill = styled.get_fill_color()
        stroke = styled.get_stroke_color()
        style_summary = styled.get_style(simple=True)
        label = m.Text(
            f"fill={fill} stroke={stroke} sw={style_summary['stroke_width']:.1f}",
            font_size=20,
        ).to_edge(m.DOWN)

        group = m.Group(styled, mirror).arrange(m.RIGHT, buff=1.0)
        self.add(group, label)
        self.wait()
