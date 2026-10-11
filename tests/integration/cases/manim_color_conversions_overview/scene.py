# Source: manim/utils/color/core.py
import manimgx as m


class ManimColorConversionsOverview(m.Scene):
    def construct(self):
        from_hex_c = m.ManimColor.from_hex("#fc6255")
        from_rgb_int = m.ManimColor.from_rgb((40, 165, 90))
        from_rgb_float = m.ManimColor.from_rgb((0.95, 0.85, 0.10))
        from_rgba_c = m.ManimColor.from_rgba((0.20, 0.55, 0.95, 1.0))
        from_hsv_c = m.ManimColor.from_hsv((0.83, 0.55, 0.85))
        from_hsl_c = m.ManimColor.from_hsl((0.55, 0.75, 0.45))
        from_int_c = m.ManimColor(0xC78D46)
        parsed = m.ManimColor.parse(["#9a72ac", "#76ddc0"])
        inverted = m.invert_color(m.ManimColor("#236b8e"))

        colors = [
            from_hex_c,
            from_rgb_int,
            from_rgb_float,
            from_rgba_c,
            from_hsv_c,
            from_hsl_c,
            from_int_c,
            parsed[0],
            parsed[1],
            inverted,
        ]

        squares = m.VGroup(
            *[m.Square(side_length=0.7, fill_color=c, fill_opacity=1.0) for c in colors]
        ).arrange(buff=0.15)
        self.add(squares)
        self.wait(1)
