import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Bayes as an area diagram").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        TOTAL_W = 6.0
        TOTAL_H = 4.0
        P_H = 0.3
        P_E_H = 0.75
        P_E_NH = 0.2

        h_w = P_H * TOTAL_W
        h_x = -TOTAL_W / 2 + h_w / 2
        nh_w = (1 - P_H) * TOTAL_W
        nh_x = -TOTAL_W / 2 + h_w + nh_w / 2

        h_rect = m.Rectangle(
            width=h_w,
            height=TOTAL_H,
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.22,
            stroke_width=2,
        ).move_to([h_x, 0, 0])
        nh_rect = m.Rectangle(
            width=nh_w,
            height=TOTAL_H,
            color=m.RED,
            fill_color=m.RED,
            fill_opacity=0.22,
            stroke_width=2,
        ).move_to([nh_x, 0, 0])

        eh_h = P_E_H * TOTAL_H
        eh_rect = m.Rectangle(
            width=h_w,
            height=eh_h,
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.7,
            stroke_width=2,
        ).move_to([h_x, TOTAL_H / 2 - eh_h / 2, 0])

        enh_h = P_E_NH * TOTAL_H
        enh_rect = m.Rectangle(
            width=nh_w,
            height=enh_h,
            color=m.RED,
            fill_color=m.RED,
            fill_opacity=0.7,
            stroke_width=2,
        ).move_to([nh_x, TOTAL_H / 2 - enh_h / 2, 0])

        h_label = m.MathTex("H").scale(0.8).move_to([h_x, -TOTAL_H / 2 - 0.35, 0])
        nh_label = (
            m.MathTex("\\neg H").scale(0.8).move_to([nh_x, -TOTAL_H / 2 - 0.35, 0])
        )
        e_label = (
            m.MathTex("E", color=m.YELLOW)
            .scale(0.9)
            .move_to(
                [-TOTAL_W / 2 - 0.4, TOTAL_H / 2 - 0.7, 0],
            )
        )

        self.play(m.Create(h_rect), m.Create(nh_rect))
        self.play(m.Write(h_label), m.Write(nh_label))
        self.play(m.Create(eh_rect), m.Create(enh_rect), m.Write(e_label))
        self.wait(2.0)
