# Source: manim/mobject/text/text_mobject.py
import manimgx as m


class TextItalicAndBoldExample(m.Scene):
    def construct(self):
        text1 = m.Text("Hello world", slant=m.ITALIC)
        text2 = m.Text("Hello world", t2s={"world": m.ITALIC})
        text3 = m.Text("Hello world", weight=m.BOLD)
        text4 = m.Text("Hello world", t2w={"world": m.BOLD})
        text5 = m.Text("Hello world", t2c={"o": m.YELLOW}, disable_ligatures=True)
        text6 = m.Text(
            "Visit us at docs.manim.community",
            t2c={"docs.manim.community": m.YELLOW},
            disable_ligatures=True,
        )
        text6.scale(1.3).shift(m.DOWN)
        self.add(text1, text2, text3, text4, text5, text6)
        m.Group(*self.mobjects).arrange(m.DOWN, buff=0.8).set(
            height=m.config.frame_height - m.LARGE_BUFF
        )
        self.wait()
