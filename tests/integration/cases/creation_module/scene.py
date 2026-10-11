# Source: manim/animation/creation.py
import manimgx as m


class CreationModule(m.Scene):
    def construct(self):
        s1 = m.Square()
        s2 = m.Square()
        s3 = m.Square()
        s4 = m.Square()
        m.VGroup(s1, s2, s3, s4).set_x(0).arrange(buff=1.9).shift(m.UP)
        s5 = m.Square()
        s6 = m.Square()
        s7 = m.Square()
        m.VGroup(s5, s6, s7).set_x(0).arrange(buff=2.6).shift(2 * m.DOWN)
        t1 = m.Text("Write", font_size=24).next_to(s1, m.UP)
        t2 = m.Text("AddTextLetterByLetter", font_size=24).next_to(s2, m.UP)
        t3 = m.Text("Create", font_size=24).next_to(s3, m.UP)
        t4 = m.Text("Uncreate", font_size=24).next_to(s4, m.UP)
        t5 = m.Text("DrawBorderThenFill", font_size=24).next_to(s5, m.UP)
        t6 = m.Text("ShowIncreasingSubsets", font_size=22).next_to(s6, m.UP)
        t7 = m.Text("ShowSubmobjectsOneByOne", font_size=22).next_to(s7, m.UP)

        self.add(s1, s2, s3, s4, s5, s6, s7, t1, t2, t3, t4, t5, t6, t7)

        texts = [m.Text("manim", font_size=29), m.Text("manim", font_size=29)]
        texts[0].move_to(s1.get_center())
        texts[1].move_to(s2.get_center())
        self.add(*texts)

        objs = [m.ManimBanner().scale(0.25) for _ in range(5)]
        objs[0].move_to(s3.get_center())
        objs[1].move_to(s4.get_center())
        objs[2].move_to(s5.get_center())
        objs[3].move_to(s6.get_center())
        objs[4].move_to(s7.get_center())
        self.add(*objs)

        self.play(
            # text creation
            m.Write(texts[0]),
            m.AddTextLetterByLetter(texts[1]),
            # mobject creation
            m.Create(objs[0]),
            m.Uncreate(objs[1]),
            m.DrawBorderThenFill(objs[2]),
            m.ShowIncreasingSubsets(objs[3]),
            m.ShowSubmobjectsOneByOne(objs[4]),
            run_time=3,
        )

        self.wait()
