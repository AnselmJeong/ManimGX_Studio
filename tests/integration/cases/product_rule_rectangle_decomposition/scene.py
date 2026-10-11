import manimgx as m

F = 2.5
G = 1.8
DF = 0.55
DG = 0.4
ORIGIN_X = -2.0
ORIGIN_Y = -1.5


class TeacherScene(m.Scene):
    def construct(self) -> None:
        rect_fg = m.Rectangle(
            width=F,
            height=G,
            color=m.YELLOW,
            fill_color=m.YELLOW,
            fill_opacity=0.4,
            stroke_width=2,
        ).move_to([ORIGIN_X + F / 2, ORIGIN_Y + G / 2, 0])
        fg_label = m.MathTex("fg", color=m.YELLOW).move_to(rect_fg.get_center())
        self.play(m.FadeIn(rect_fg), m.Write(fg_label))
        self.wait(0.3)

        strip_gdf = m.Rectangle(
            width=DF,
            height=G,
            color=m.GREEN,
            fill_color=m.GREEN,
            fill_opacity=0.4,
            stroke_width=2,
        ).move_to([ORIGIN_X + F + DF / 2, ORIGIN_Y + G / 2, 0])
        gdf_label = (
            m.MathTex("g\\,df", color=m.GREEN)
            .scale(0.6)
            .move_to(strip_gdf.get_center())
        )

        strip_fdg = m.Rectangle(
            width=F,
            height=DG,
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.4,
            stroke_width=2,
        ).move_to([ORIGIN_X + F / 2, ORIGIN_Y + G + DG / 2, 0])
        fdg_label = (
            m.MathTex("f\\,dg", color=m.BLUE).scale(0.6).move_to(strip_fdg.get_center())
        )

        corner = m.Rectangle(
            width=DF,
            height=DG,
            color=m.RED,
            fill_color=m.RED,
            fill_opacity=0.6,
            stroke_width=1.5,
        ).move_to([ORIGIN_X + F + DF / 2, ORIGIN_Y + G + DG / 2, 0])
        corner_label = (
            m.MathTex("df\\,dg", color=m.RED)
            .scale(0.35)
            .next_to(
                corner,
                m.UR,
                buff=0.06,
            )
        )

        self.play(m.FadeIn(strip_gdf), m.Write(gdf_label))
        self.play(m.FadeIn(strip_fdg), m.Write(fdg_label))
        self.play(m.FadeIn(corner), m.Write(corner_label))

        formula = m.MathTex(
            "d(fg) \\approx g\\,df + f\\,dg",
        ).to_edge(m.DOWN, buff=0.5)
        self.play(m.Write(formula))
        self.wait(2.0)
