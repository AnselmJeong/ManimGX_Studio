# Source: manim/mobject/text/text_mobject.py
import manimgx as m


class MultipleFonts(m.Scene):
    def construct(self):
        morning = m.Text("வணக்கம்", font="sans-serif")
        japanese = m.Text(
            "日本へようこそ",
            t2c={"日本": m.BLUE},
        )  # works same as ``Text``.
        mess = m.Text("Multi-Language", weight=m.BOLD)
        russ = m.Text("Здравствуйте मस नम म ", font="sans-serif")
        hin = m.Text("नमस्ते", font="sans-serif")
        arb = m.Text(
            "صباح الخير \n تشرفت بمقابلتك", font="sans-serif"
        )  # don't mix RTL and LTR languages nothing shows up then ;-)
        chinese = m.Text("臂猿「黛比」帶著孩子", font="sans-serif")
        self.add(morning, japanese, mess, russ, hin, arb, chinese)
        for i, mobj in enumerate(self.mobjects):
            mobj.shift(m.DOWN * (i - 3))
