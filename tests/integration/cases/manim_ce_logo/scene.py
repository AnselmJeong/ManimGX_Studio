# Source: docs/source/examples.rst
import manimgx as m


class ManimCELogo(m.Scene):
    def construct(self):
        self.camera.background_color = "#ece6e2"
        logo_green = "#87c2a5"
        logo_blue = "#525893"
        logo_red = "#e07a5f"
        logo_black = "#343434"
        ds_m = m.MathTex(r"\mathbb{M}", fill_color=logo_black).scale(7)
        ds_m.shift(2.25 * m.LEFT + 1.5 * m.UP)
        circle = m.Circle(color=logo_green, fill_opacity=1).shift(m.LEFT)
        square = m.Square(color=logo_blue, fill_opacity=1).shift(m.UP)
        triangle = m.Triangle(color=logo_red, fill_opacity=1).shift(m.RIGHT)
        logo = m.VGroup(triangle, square, circle, ds_m)  # order matters
        logo.move_to(m.ORIGIN)
        self.add(logo)
        self.wait()
